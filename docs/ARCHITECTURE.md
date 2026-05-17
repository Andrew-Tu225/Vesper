# Vesper Architecture

## Current State

Vesper is an open-source, self-hostable app for converting Slack activity into reviewed LinkedIn drafts.

Implemented today:

- Google login and Redis-backed sessions
- Slack OAuth and encrypted bot token storage
- LinkedIn OAuth and encrypted access/refresh token storage
- Slack channel onboarding
- Scheduled Slack intake
- Batch classification with OpenAI
- Slack message embeddings stored in pgvector
- Draft enrichment and generation
- Slack approval/rewrite/reject actions
- Queue, dashboard, calendar, and settings frontend views
- Scheduled LinkedIn publishing
- Celery Beat maintenance jobs

Not currently implemented:

- Gmail intake
- LinkedIn organization-page posting
- Stripe billing or any paywall
- OpenRouter provider switching

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TanStack Query |
| API | FastAPI |
| ORM | SQLAlchemy 2 async |
| Database | PostgreSQL 16 with pgvector |
| Migrations | Alembic |
| Queue/cache | Redis |
| Worker | Celery |
| Crypto | AES-256-GCM via `cryptography` |
| Slack | `slack-sdk` |
| AI | OpenAI API |

## Runtime Processes

| Process | Command | Purpose |
|---------|---------|---------|
| API | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | FastAPI app |
| Worker | `celery -A app.workers.celery_app worker --loglevel=info -Q draft_pipeline,intake,publishing,maintenance` | Executes async product work |
| Beat | `celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule` | Dispatches scheduled jobs |
| Frontend | nginx in Docker, Vite dev server locally | Serves React app and proxies `/api` |

## Data Model

```text
users
  -> workspace (owner_user_id)
       -> workspace_member
       -> oauth_token
       -> content_signal
            -> draft_post
       -> slack_message_embedding
       -> audit_log
```

Important tables:

- `workspace`: workspace identity, onboarding state, and JSON settings
- `oauth_token`: encrypted Slack and LinkedIn tokens
- `content_signal`: worthy Slack-derived content opportunities
- `draft_post`: generated LinkedIn draft variants and publishing state
- `slack_message_embedding`: pgvector context store for Slack messages
- `audit_log`: important actions and token refresh events

OAuth token providers:

| Provider | Level | Description |
|----------|-------|-------------|
| `slack` | Workspace | Slack bot token, `user_id` is null |
| `linkedin_personal` | User | LinkedIn personal access/refresh tokens |

## Onboarding Flow

```text
Google login
  -> create user and workspace if needed
  -> Slack OAuth
  -> LinkedIn OAuth
  -> channel selection
  -> onboarding_complete = true
```

Workspace steps:

- `connect_slack`
- `connect_linkedin`
- `channels_setup`
- `done`

## API Surface

Public or semi-public:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | DB and Redis readiness |
| `GET` | `/api/auth/google/login` | Start Google OAuth |
| `GET` | `/api/auth/google/callback` | Complete Google OAuth |
| `POST` | `/api/webhooks/slack/actions` | Slack interactivity endpoint, verified by Slack signature |

Authenticated:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/auth/me` | Current user |
| `POST` | `/api/auth/google/logout` | Logout |
| `GET` | `/api/oauth/slack/install` | Start Slack OAuth |
| `GET` | `/api/oauth/slack/status` | Slack connection status |
| `GET` | `/api/oauth/linkedin/install` | Start LinkedIn OAuth |
| `GET` | `/api/oauth/linkedin/status` | LinkedIn connection status |
| `GET` | `/api/onboarding/channels` | List Slack channels |
| `POST` | `/api/onboarding/channels` | Save monitored channels |
| `GET` | `/api/signals` | List signals |
| `GET` | `/api/signals/stats` | Dashboard stats |
| `GET` | `/api/signals/{signal_id}` | Signal detail |
| `POST` | `/api/signals/{signal_id}/approve` | Approve and optionally schedule a draft |
| `POST` | `/api/signals/{signal_id}/reject` | Reject a signal |
| `POST` | `/api/signals/{signal_id}/rewrite` | Request a draft rewrite |

## Celery Queues

| Queue | Tasks |
|-------|-------|
| `intake` | `scan_slack_channels`, `scan_gmail_inbox` stub |
| `draft_pipeline` | `classify_signal`, `enrich_context`, `generate_draft`, `rewrite_draft` |
| `publishing` | `publish_post` |
| `maintenance` | `dispatch_intake_scans`, `refresh_oauth_tokens`, `dispatch_due_posts`, `purge_slack_message_embeddings`, `cleanup_stale_signals` stub |

Beat schedule:

- Intake scan fan-out: 00:00 and 12:00 UTC
- LinkedIn token refresh: daily at 02:00 UTC
- Slack embedding purge: daily at 03:00 UTC
- Due post dispatch: every 5 minutes

## Intake And Draft Pipeline

```text
Celery Beat
  -> dispatch_intake_scans
  -> scan_slack_channels(workspace_id)
       -> fetch configured Slack channels
       -> classify message window
       -> embed selected messages
       -> dedupe with Redis SETNX
       -> create ContentSignal
       -> run_draft_pipeline(signal_id)
            -> classify_signal
            -> enrich_context
            -> generate_draft
            -> post Slack approval card
```

Manual Slack actions can approve, reject, or request a rewrite. Approved drafts can be scheduled; Beat dispatches due posts to LinkedIn through the publishing queue.

## Configuration Notes

- Backend settings load `../.env` and `backend/.env`.
- Docker Compose overrides `DATABASE_URL` and `REDIS_URL` for internal service hostnames.
- The frontend calls relative `/api` URLs. In Docker, nginx proxies `/api` to the backend. In dev, Vite proxies `/api` to `VITE_API_PROXY_TARGET`.
- `APP_SECRET_KEY` must stay stable for a deployment because it encrypts stored OAuth tokens.
