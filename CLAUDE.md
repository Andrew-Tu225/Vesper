# Vesper — AI Content Assistant

Slack-first AI content assistant that turns internal signals (Slack messages, emails) into ready-to-publish LinkedIn posts, with human approval always in the loop.

## Stack

**Backend:** Python + FastAPI, PostgreSQL + pgvector, Celery/RQ + Redis
**Frontend:** React (web dashboard)
**AI:** OpenAI (text-embedding-3-small for embeddings; cheap model for classification; stronger model for generation)
**Integrations:** Slack SDK for Python, Gmail API, LinkedIn Marketing API

## Project Structure (target)

```
vesper/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (webhooks, OAuth, REST)
│   │   ├── workers/      # Celery/RQ tasks (email polling, AI pipeline, publishing)
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic (classifier, drafter, embedder, publisher)
│   │   └── integrations/ # Slack, Gmail, LinkedIn clients
│   ├── migrations/       # Alembic migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/        # Onboarding, Queue, Calendar, Settings, Style Library
│   │   └── components/
│   └── tests/
└── CLAUDE.md
```

## Core Data Model

### `content_signal`
Unified model for candidates from Slack or email:
- `source_type`: `slack` | `email`
- `text`: raw message/thread
- `summary`: AI-extracted summary
- `signal_type`: `customer_praise` | `product_win` | `launch_update` | `hiring` | `founder_insight`
- `sensitivity`: redaction flag
- `status`: `detected` → `drafted` → `in_review` → `approved` → `scheduled` → `posted`

### Style Library
- Approved + published posts stored as pgvector embeddings (`text-embedding-3-small`)
- Cosine similarity search retrieves top 2–3 examples at draft time (few-shot injection)
- Auto-updated on every approved + published post

## AI Pipeline

1. **Classify** — cheap model (GPT-4o-mini or Gemini Flash-Lite) determines content-worthy vs noise + signal type
2. **Redact** — same cheap model removes sensitive details before drafting
3. **Retrieve** — cosine similarity against style library → top 2–3 past posts as few-shot examples
4. **Generate** — stronger model (GPT-4o or Gemini Pro) writes 2–3 LinkedIn post variants using the prompt:
   ```
   Here are examples of how [Company] writes LinkedIn posts:
   [Example 1]
   [Example 2]
   Now write a post about: [signal summary]
   Match the tone, length, and structure of the examples above.
   ```
5. **Route** — draft cards posted to Slack `#social-queue` with Approve / Reject / Rewrite / Schedule actions

## Integration Details

### Slack
- Custom app (free + paid plan compatible)
- Events API for monitoring selected channels
- Message action: "Create LinkedIn draft" on any message
- Interactive blocks for approval cards in `#social-queue`
- Optional App Home: queue snapshot + "needs approval" list

### Email
- Gmail API (watch selected labels/folders)
- Periodic polling via background worker — not a full inbox assistant
- Email threads → `content_signal` → same Slack review flow

### LinkedIn
- OAuth 2.0 authorization code flow
- Company-page posting first; personal profile is post-MVP
- Scheduling: pick datetime or "next 9am workday"
- Retry logic for failed posts

## Implementation Phases

| Phase | Scope |
|-------|-------|
| 1 — Foundation | Repo, FastAPI skeleton, PostgreSQL schema + pgvector, React shell, Slack + LinkedIn OAuth |
| 2 — Slack Pipeline | Channel monitoring, message action → content_signal, AI classify + draft, approval cards |
| 3 — Email Pipeline | Gmail OAuth, folder config, periodic fetch + classify, push to Slack review |
| 4 — Brand-Voice Memory | Style library UI, embedding pipeline, retrieval wired into draft generation, auto-add on publish |
| 5 — Publishing & Calendar | LinkedIn posting, scheduling, queue + calendar views, failure handling + retries |
| 6 — Safety & Polish | Redaction pass, prompt tuning, error handling, token expiry flows, logging |

## Out of Scope (MVP)

- Microsoft Teams / meeting transcript ingestion
- Deep analytics or content scoring
- Cross-platform publishing (X, Facebook, etc.)
- Autonomous posting without human approval
- Enterprise roles/permissions and compliance
- Per-author voice profiles (one brand voice per workspace for MVP)

## Key Constraints

- No fine-tuning — RAG-style prompt injection only
- One brand voice per workspace
- Minimum 5 seed posts to initialize style library
- All posts require human approval before going live
- Target AI cost: ~$5–15/month for a small pilot

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Worker
celery -A app.workers worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev

# Tests
pytest backend/tests/
npm test --prefix frontend
```

## Security Notes

- All OAuth tokens encrypted at rest
- Slack request signatures verified on every webhook
- Redaction pass runs before any draft is sent to Slack
- No raw email/message content stored beyond what's needed for the signal
- LinkedIn tokens scoped to minimum required permissions (w_member_social or w_organization_social)
