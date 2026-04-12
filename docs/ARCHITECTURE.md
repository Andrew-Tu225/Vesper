# Vesper — Architecture

## Current State (Phase 2.1 complete)

Foundation is in place: database schema, async infrastructure, crypto layer, Docker setup, and all three OAuth flows (Google login, Slack install, LinkedIn install).
Celery worker layer added: 5 named queues, batch intake scanner stub, draft pipeline task stubs, proactive LinkedIn token refresh via Celery Beat.

Phase 2.1 added the LLM service layer:
- `services/openai_client.py` — async client factory; routes to OpenRouter (dev) or direct OpenAI (prod) via config
- `services/schemas.py` — shared Pydantic schemas: `SlackMessage`, `ContentSignalCandidate`, `BatchClassifyResponse`, `RedactResult`
- `services/classifier.py` — `batch_classify()`: one GPT-4o-mini call per scan window; reads flat Slack message stream, groups related messages into `ContentSignalCandidate` objects (worthy signals only, noise excluded at this step)

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
| Slack | slack-sdk 3 |

## Data Model

```
users
  └── workspace (owner_user_id)
        ├── workspace_member (workspace_id, user_id)
        ├── oauth_token (workspace_id, user_id?)
        ├── content_signal (workspace_id)
        │     └── draft_post (content_signal_id, workspace_id)
        ├── style_entry (workspace_id, draft_post_id?)
        └── audit_log (workspace_id)
```

### Key tables

**`content_signal`** — the core entity. Created only when an inbound event is classified as content-worthy (classify-first pipeline). Never stores raw noise.

| Column | Type | Notes |
|--------|------|-------|
| `source_type` | `varchar(16)` | `slack` or `gmail` |
| `source_id` | `varchar(255)` | Original message_ts or email_id — dedup key |
| `signal_type` | `varchar(32)` | `customer_praise` \| `product_win` \| `launch_update` \| `hiring` \| `founder_insight` |
| `original_text` | text | Raw message text |
| `redacted_text` | text | Redacted version (sensitive details removed) |
| `summary` | text | AI-generated summary |
| `sensitivity` | `varchar(16)` | `unknown` \| `low` \| `medium` \| `high` |
| `status` | `varchar(32)` | `detected` → `classified` → `enriched` → `drafted` → `in_review` → `approved` → `scheduled` → `posted` |
| `raw_payload` | jsonb | Original Slack/Gmail envelope — stored only for worthy signals |

**`oauth_token`** — all OAuth tokens encrypted with AES-256-GCM before storage. Three-column layout: `encrypted_token`, `nonce`, `tag`. Nonce is enforced unique at the DB level (GCM security requirement).

**`style_entry`** — brand-voice memory. Stores `vector(1536)` embeddings (text-embedding-3-small) of approved posts. Indexed with `ivfflat` for cosine similarity search.

## Content Intake Model

Auto content discovery runs as a **scheduled batch scan**, not real-time event processing.
A single message rarely has enough context to judge content worthiness. Scanning an
accumulated window gives the classifier full threads, replies, and email chains.

```
Celery Beat (configurable per workspace, default 3×/day)
        │
        ├─ scan_slack_channels   (intake queue)
        │    fetch messages from enrichment_channels since last_slack_scanned_at
        │    batch classify full list → one LLM call
        │    create ContentSignal only for worthy items
        │    dispatch draft_pipeline for each winner
        │    update last_slack_scanned_at
        │
        └─ scan_gmail_inbox      (intake queue)
             fetch emails from configured labels since last_gmail_scanned_at
             batch classify full list → one LLM call
             create ContentSignal only for worthy items
             dispatch draft_pipeline for each winner
             update last_gmail_scanned_at

Manual trigger (always available, independent of schedule)
        Slack "Create LinkedIn draft" message action
          → FastAPI webhook → ContentSignal → draft_pipeline
```

Slack Events API webhooks are used **only** for the manual message action.
Auto channel monitoring uses the batch scanner, not webhooks.

Scan checkpoints (`last_slack_scanned_at`, `last_gmail_scanned_at`) are stored in
`workspace.settings` JSONB and updated after each successful scan run.

## AI Pipeline (Phase 2+)

Batch classification happens at **intake time** — before any `ContentSignal` is written to the DB.
Only signals the LLM classifies as content-worthy enter the draft pipeline.

```
Intake (scan_slack_channels)
        │
        ├─ Batch classify   — GPT-4o-mini, one call for entire scan window
        │                     reads flat chronological Slack message stream
        │                     groups related messages into signals (threads, follow-ups)
        │                     extracts signal_type + summary per cluster
        │                     noise is dropped here — never reaches the DB
        │
        ├─ Dedup            — Redis SETNX dedup:{workspace_id}:slack:{source_ids[0]} (24h TTL)
        │                     already-seen signals are skipped
        │
        └─ INSERT ContentSignal (status=detected, signal_type, summary, source_id=source_ids[0])
                              raw_payload stores all source_ids + original message texts
                              dispatch run_draft_pipeline(signal_id)

Draft pipeline queue (per signal)
        │
        ├─ 1. classify_signal   — no LLM call; signal_type + summary pre-set at intake
        │                         writes original_text from raw_payload
        │                         status → classified
        │
        ├─ 2. enrich_context    — GPT-4o-mini agent with tool use (max 5 iterations)
        │                         retrieves additional Slack threads / email Re: chains
        │                         self-judges whether context is sufficient
        │                         writes context_summary to metadata_['enrichment']
        │                         status → enriched
        │
        │    Slack tools: get_slack_thread, get_slack_channel_history,
        │                 search_slack_messages
        │    Email tools: get_email_thread, search_emails_by_sender,
        │                 search_emails (all live Gmail API calls)
        │
        ├─ 3. redact_signal     — GPT-4o-mini removes PII, customer names, internal specifics
        │                         writes redacted_text, sets sensitivity (low/medium/high)
        │                         HARD GATE: failure sets status=failed, pipeline stops
        │
        ├─ 4. generate_draft    — GPT-4o writes 2–3 LinkedIn variants
        │                         uses context_summary + top 2–3 style-library entries
        │                         (pgvector cosine similarity) as few-shot context
        │                         creates DraftPost records; status → drafted
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
  │◀── 302 /onboarding?step=seed_style_library ─────────────│
```

## Celery Queues

| Queue | Purpose |
|-------|---------|
| `draft_pipeline` | Per-signal tasks: classify → enrich → redact → generate |
| `style_library` | Style-entry embedding and pgvector upserts |
| `intake` | Scheduled batch scans: Slack channels + Gmail inbox |
| `publishing` | LinkedIn post delivery |
| `maintenance` | LinkedIn token refresh (Beat), cleanup |

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
│  :5173      │   │  :8000      │   │  queues: ai etc.  │
└─────────────┘   └──────┬──────┘   └────────┬──────────┘
                         │                   │
              ┌──────────┴──────────┐         │
              │                     │         │
         ┌────▼──────┐        ┌─────▼─────────▼──┐
         │ PostgreSQL│        │      Redis        │
         │  +pgvector│        │  (broker + cache) │
         │  :5432    │        │  :6379            │
         └───────────┘        └───────────────────┘
```

## Implementation Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 — Foundation | Repo, FastAPI skeleton, DB schema, pgvector, crypto, Docker, Google + Slack + LinkedIn OAuth | ✅ Done |
| 2.1 — LLM Service Layer | OpenAI client factory, shared schemas, batch classifier | ✅ Done |
| 2.2 — Slack Client | Sync Slack WebClient wrapper for Celery workers | 🔜 Next |
| 2.3 — Slack Actions Endpoint | Interactive button handler (approve/reject/rewrite/schedule) | Planned |
| 2.4 — Batch Intake Scanner | scan_slack_channels full implementation | Planned |
| 2.5 — Draft Pipeline | Full LLM implementations: enrich, redact, generate | Planned |
| 2.6 — Approval Service | approve/reject/rewrite/schedule handlers | Planned |
| 2.7–2.9 — REST API + Frontend + Tests | Signals/drafts API, Queue page, integration tests | Planned |
| 3 — Email Pipeline | Gmail OAuth, folder config, periodic fetch | Planned |
| 4 — Brand-Voice Memory | Style library UI, embedding pipeline, retrieval | Planned |
| 5 — Publishing & Calendar | LinkedIn posting, scheduling, queue + calendar views | Planned |
| 6 — Safety & Polish | Redaction tuning, error handling, Slack token expiry warnings | Planned |
