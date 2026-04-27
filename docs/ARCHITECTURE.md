# Vesper — Architecture

## Current State (Phase 2.2 complete)

Foundation, Celery worker layer, and LLM service layer are all in place.

Phase 2.1 added:
- `services/openai_client.py` — async client factory; routes to OpenRouter (dev) or direct OpenAI (prod)
- `services/schemas.py` — shared Pydantic schemas: `SlackMessage`, `ContentSignalCandidate`, `BatchClassifyResponse`
- `services/classifier.py` — `batch_classify()`: one GPT-4o-mini call per scan window; returns content signal candidates **and** `embed_message_ids` for enrichment context storage

Phase 2.2 added:
- `services/slack_client.py` — sync `WebClient` wrapper for Celery workers (decrypts bot token, wraps channel history + thread + post/update)
- `services/embedder.py` — `embed_texts()`: batch call to `text-embedding-3-small`; produces 1536-dim vectors
- `models/slack_message_embedding.py` + migration `002` — stores embedded Slack messages for cross-day enrichment context (30-day TTL, IVFFlat index for cosine search)
- `app/db_sync.py` — shared psycopg2 `ThreadedConnectionPool` for all Celery workers
- `workers/maintenance.purge_slack_message_embeddings` — Beat task deletes rows older than 30 days (daily 03:00 UTC)
- Onboarding step updated to `channels_setup`

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115 (async) |
| ORM | SQLAlchemy 2.0 (asyncio) |
| Database | PostgreSQL 16 + pgvector |
| Migrations | Alembic (async) |
| Worker | Celery 5 + Redis 7 |
| Crypto | AES-256-GCM (`cryptography` library) |
| HTTP client | httpx |
| Slack | slack-sdk 3 (sync `WebClient` in workers) |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |

## Data Model

```
users
  └── workspace (owner_user_id)
        ├── workspace_member (workspace_id, user_id)
        ├── oauth_token (workspace_id, user_id?)
        ├── content_signal (workspace_id)
        │     └── draft_post (content_signal_id, workspace_id)
        ├── slack_message_embedding (workspace_id)   ← enrichment context; 30-day TTL
        └── audit_log (workspace_id)
```

> **MVP:** `generate_draft` uses zero-shot GPT-4o. Brand-voice style library is out of scope.

### Key tables

**`content_signal`** — the core entity. Created only after batch classification identifies a worthy signal. Never stores noise.

| Column | Type | Notes |
|--------|------|-------|
| `source_type` | `varchar(16)` | `slack` or `gmail` |
| `source_id` | `varchar(255)` | `source_ids[0]` from classifier — dedup anchor |
| `signal_type` | `varchar(32)` | `customer_praise` \| `product_win` \| `launch_update` \| `hiring` \| `founder_insight` |
| `original_text` | text | Reconstructed from `raw_payload` messages |
| `redacted_text` | text | PII-stripped version |
| `summary` | text | LLM-extracted summary (set at intake time by classifier) |
| `sensitivity` | `varchar(16)` | `unknown` \| `low` \| `medium` \| `high` |
| `status` | `varchar(32)` | `detected` → `classified` → `enriched` → `drafted` → `in_review` → `approved` → `scheduled` → `posted` |
| `raw_payload` | jsonb | All `source_ids` + original message texts |

**`slack_message_embedding`** — enrichment context store. The classifier's `embed_message_ids` are looked up in `msg_lookup`, embedded via `text-embedding-3-small`, and upserted here. The `enrich_context` pipeline task uses pgvector cosine search against this table to find relevant context spanning multiple days.

| Column | Type | Notes |
|--------|------|-------|
| `workspace_id` | uuid | FK → workspace |
| `channel_id` | varchar | Slack channel ID |
| `message_ts` | varchar | Slack message timestamp — dedup key |
| `author_id` | varchar | Slack user ID |
| `text` | text | Raw message text |
| `embedding` | vector(1536) | `text-embedding-3-small` output |
| `stored_at` | timestamptz | Used for 30-day TTL cleanup |

Unique index on `(workspace_id, channel_id, message_ts)`. IVFFlat index (`lists=10`) for cosine similarity. Index on `stored_at` for TTL DELETE.

**`oauth_token`** — all OAuth tokens encrypted with AES-256-GCM. Three-column layout: `encrypted_token`, `nonce`, `tag`. Nonce enforced unique at DB level (GCM security requirement).

| `provider` | `user_id` | Description |
|---|---|---|
| `slack` | NULL | Workspace-level Slack bot token |
| `linkedin_personal` | user.id | User-level LinkedIn personal profile token |

LinkedIn tokens use `provider='linkedin_personal'` with `user_id` set (user-level). Scopes: `openid profile email w_member_social`. `workspace.linkedin_org_id` is reserved for future org-page posting (requires LinkedIn Marketing Developer Platform access) but is currently unused.

## Onboarding Step Progression

```
workspace.onboarding_step

"connect_slack"     ← default on workspace creation
        ↓ (Slack OAuth installs bot, creates workspace)
"connect_linkedin"
        ↓ (LinkedIn OAuth stores access + refresh tokens)
"channels_setup"
        ↓ (user selects enrichment_channels; saved to workspace.settings)
onboarding_complete = True
```

## Content Intake Model

Auto content discovery runs as a **scheduled batch scan**, not real-time event processing.

```
Celery Beat (configurable per workspace, default 3×/day)
        │
        └─ scan_slack_channels   (intake queue)
             fetch messages from enrichment_channels since last_slack_scanned_at
             batch classify → one GPT-4o-mini call (candidates + embed_message_ids)
             embed embed_message_ids → upsert slack_message_embedding rows
             dedup candidates via Redis SETNX (24h TTL)
             create ContentSignal for each new worthy candidate
             dispatch run_draft_pipeline(signal_id) for each
             update last_slack_scanned_at
```

Slack Events API webhooks are used **only** for the manual "Create LinkedIn draft" message action (Phase 2.4+). Auto channel monitoring uses the batch scanner.

## AI Pipeline

```
Intake (scan_slack_channels)
        │
        ├─ Batch classify   — GPT-4o-mini, one call for entire scan window
        │                     Task 1: groups related messages into ContentSignalCandidates
        │                     Task 2: flags messages for enrichment embedding
        │                     noise dropped here — never reaches the DB
        │
        ├─ Embed            — text-embedding-3-small; upsert slack_message_embedding
        │
        ├─ Dedup            — Redis SETNX dedup:{workspace_id}:slack:{source_ids[0]} (24h TTL)
        │
        └─ INSERT ContentSignal (status=detected)
           dispatch run_draft_pipeline(signal_id)

Draft pipeline (per signal)
        │
        ├─ 1. classify_signal   — no LLM call; signal_type + summary pre-set at intake
        │                         writes original_text from raw_payload; status → classified
        │
        ├─ 2. enrich_context    — GPT-4o-mini agent (max 5 iterations)
        │                         tools: get_slack_thread, search_context (pgvector over
        │                         slack_message_embedding — spans 30 days of context)
        │                         writes context_summary; status → enriched
        │
        ├─ 3. redact_signal     — GPT-4o-mini strips PII, customer names, internal specifics
        │                         HARD GATE: failure → status=failed, pipeline stops
        │
        ├─ 4. generate_draft    — GPT-4o zero-shot (no style library in MVP)
        │                         3 LinkedIn post variants; inserts DraftPost records
        │                         status → drafted
        │
        └─ 5. route             — approval card posted to Slack social_queue_channel
                                  Approve / Reject / Rewrite / Schedule buttons
                                  status → in_review
```

## API Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/health` | ✅ Live | DB + Redis liveness/readiness check |
| GET | `/api/auth/google/login` | ✅ Live | Redirect to Google OAuth consent screen |
| GET | `/api/auth/google/callback` | ✅ Live | Exchange code, upsert user, set session cookie |
| POST | `/api/auth/google/logout` | ✅ Live | Delete server-side session, clear cookie |
| GET | `/api/auth/google/me` | ✅ Live | Return current authenticated user |
| GET | `/api/oauth/slack/install` | ✅ Live | Redirect authenticated user to Slack OAuth consent |
| GET | `/api/oauth/slack/callback` | ✅ Live | Exchange code, encrypt + store bot token, upsert workspace |
| GET | `/api/oauth/linkedin/install` | ✅ Live | Redirect authenticated user to LinkedIn OAuth consent |
| GET | `/api/oauth/linkedin/callback` | ✅ Live | Exchange code, encrypt + store access + refresh tokens |

### Authentication

All routes except `/health`, `/api/auth/google/login`, and `/api/auth/google/callback` require an authenticated session. The session is a server-side Redis key (24h TTL) identified by an HttpOnly `vesper_session` cookie set at Google login.

### OAuth flow summary

```
Browser                     Backend                      Provider
  │                            │                            │
  │── GET /api/auth/google/login ──▶ generate state ──────▶ │
  │◀── 302 accounts.google.com/o/oauth2/auth ───────────────│
  │                            │                            │
  │── GET /api/auth/google/callback?code=&state= ──────────▶│
  │                            │── exchange code ──────────▶│
  │                            │◀── id_token (JWT) ─────────│
  │                            │   upsert user, set cookie  │
  │◀── 302 /dashboard ─────────│                            │
  │                            │                            │
  │── GET /api/oauth/slack/install (cookie) ───────────────▶│
  │◀── 302 slack.com/oauth/v2/authorize ────────────────────│
  │── GET /api/oauth/slack/callback?code=&state= ──────────▶│
  │                            │── exchange code ──────────▶│
  │                            │◀── bot token ──────────────│
  │                            │   encrypt + store token    │
  │◀── 302 /onboarding?step=connect_linkedin ───────────────│
  │                            │                            │
  │── GET /api/oauth/linkedin/install (cookie) ────────────▶│
  │◀── 302 linkedin.com/oauth/v2/authorization ─────────────│
  │── GET /api/oauth/linkedin/callback?code=&state= ───────▶│
  │                            │── exchange code ──────────▶│
  │                            │◀── access + refresh tokens─│
  │                            │   encrypt + store both     │
  │◀── 302 /onboarding?step=channels_setup ─────────────────│
```

## Celery Queues

| Queue | Purpose |
|-------|---------|
| `draft_pipeline` | Per-signal tasks: classify → enrich → redact → generate |
| `intake` | Scheduled batch scans: Slack channels |
| `publishing` | LinkedIn post delivery |
| `maintenance` | LinkedIn token refresh, purge embeddings (Beat) |

## Crypto Layer (`backend/app/crypto.py`)

All OAuth tokens use AES-256-GCM. The `APP_SECRET_KEY` (32-byte hex) is loaded from settings at call time (not at import time) to avoid circular imports.

```
encrypt(plaintext: str) → EncryptedToken(ciphertext, nonce, tag)
decrypt(token: EncryptedToken) → str   # raises TokenDecryptionError on auth failure
token_to_b64(token) → str              # pack for transport across API boundaries
b64_to_token(packed) → EncryptedToken  # unpack
```

## Infrastructure (Docker Compose)

```
┌─────────────┐   ┌─────────────┐   ┌───────────────────┐
│  frontend   │   │   backend   │   │      worker       │
│  (React)    │──▶│  (FastAPI)  │   │  (Celery)         │
│  :5173      │   │  :8000      │   │  draft_pipeline   │
└─────────────┘   └──────┬──────┘   │  intake           │
                         │          │  publishing        │
              ┌──────────┴──────────┤  maintenance       │
              │                     └────────┬──────────┘
         ┌────▼──────┐                       │
         │ PostgreSQL│        ┌──────────────▼──┐
         │  +pgvector│        │      Redis        │
         │  :5432    │        │  (broker + cache) │
         └───────────┘        └───────────────────┘
```

## Implementation Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 — Foundation | Repo, FastAPI skeleton, DB schema, pgvector, crypto, Docker, Google + Slack + LinkedIn OAuth | ✅ Done |
| 2.1 — LLM Service Layer | OpenAI client factory, shared schemas, batch classifier | ✅ Done |
| 2.2 — Slack Client + Embedding | Sync Slack client, text embedder, slack_message_embedding model + migration, shared DB pool, purge task | ✅ Done |
| 2.3 — Channels Setup API | Channel selection endpoint, onboarding completion | 🔜 Next |
| 2.4 — Slack Actions Endpoint | Interactive button handler (approve/reject/rewrite/schedule) | Planned |
| 2.5 — Batch Intake Scanner | scan_slack_channels full implementation (classify + embed + create signals) | Planned |
| 2.6 — Draft Pipeline | Full LLM: enrich (pgvector + thread tools), redact (hard gate), generate (zero-shot GPT-4o) | Planned |
| 2.7 — Approval Service | approve/reject/rewrite/schedule handlers | Planned |
| 2.8–2.10 — REST API + Frontend + Tests | Signals/drafts API, Queue page, integration tests | Planned |
| 3 — Email Pipeline | Gmail OAuth, folder config, periodic fetch | Planned |
| 4 — Publishing & Calendar | LinkedIn posting, scheduling, queue + calendar views | Planned |
| 5 — Safety & Polish | Redaction tuning, error handling, Slack token expiry warnings | Planned |
