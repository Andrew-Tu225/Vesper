# Vesper — Architecture

## Current State (Phase 1.4 in progress)

Foundation is in place: database schema, async infrastructure, crypto layer, OAuth route stubs, and Docker setup.
Celery worker layer added: 5 named queues, batch intake scanner model, draft pipeline task stubs, workspace settings schema.

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

```
ContentSignal (status=detected)
        │
        ▼ draft_pipeline queue
        │
        ├─ 1. Classify      — GPT-4o-mini (batch, one call per scan)
        │                     content-worthy? signal_type? sensitivity?
        │                     status → classified
        │
        ├─ 2. Enrich        — GPT-4o-mini agent with tool use (max 5 iterations)
        │                     retrieves relevant Slack threads / email Re: chains
        │                     self-judges whether context is sufficient
        │                     produces context_summary in metadata_['enrichment']
        │                     status → enriched
        │
        │    Slack tools: get_slack_thread, get_slack_channel_history,
        │                 search_slack_messages
        │    Email tools: get_email_thread, search_emails_by_sender,
        │                 search_emails (all live Gmail API calls)
        │
        ├─ 3. Redact        — GPT-4o-mini removes sensitive details
        │                     populates redacted_text, sets sensitivity
        │
        ├─ 4. Generate      — GPT-4o writes 2–3 LinkedIn variants
        │                     uses context_summary + top 2–3 style-library
        │                     examples (pgvector cosine search) as few-shot context
        │                     status → drafted
        │
        └─ 5. Route         — approval cards posted to Slack #vesper-ai
                              Approve / Reject / Rewrite / Schedule buttons
                              status → in_review
```

Deduplication: Redis `SETNX dedup:{workspace_id}:{source_type}:{source_id}` with TTL — prevents double-processing before the DB write.

## API Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/health` | Live | DB + Redis liveness/readiness check |
| GET | `/api/oauth/slack/install` | Stub (Phase 2) | Redirect to Slack OAuth consent |
| GET | `/api/oauth/slack/callback` | Stub (Phase 2) | Handle Slack OAuth callback |
| GET | `/api/oauth/linkedin/install` | Stub (Phase 5) | Redirect to LinkedIn OAuth consent |
| GET | `/api/oauth/linkedin/callback` | Stub (Phase 5) | Handle LinkedIn OAuth callback |

## Celery Queues

| Queue | Purpose |
|-------|---------|
| `ai` | Classification, redaction, generation |
| `enrichment` | Embedding, style-library updates |
| `polling` | Gmail periodic fetch |
| `publishing` | LinkedIn post delivery |
| `maintenance` | Token refresh, cleanup |

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
| 1 — Foundation | Repo, FastAPI skeleton, DB schema, pgvector, crypto, Docker | ✅ Done |
| 2 — Slack Pipeline | Channel monitoring, classify + draft, Slack approval cards | 🔜 Next |
| 3 — Email Pipeline | Gmail OAuth, folder config, periodic fetch | Planned |
| 4 — Brand-Voice Memory | Style library UI, embedding pipeline, retrieval | Planned |
| 5 — Publishing & Calendar | LinkedIn posting, scheduling, queue + calendar views | Planned |
| 6 — Safety & Polish | Redaction tuning, error handling, token refresh flows | Planned |
