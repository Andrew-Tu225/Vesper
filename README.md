# Vesper

Open-source AI content assistant for turning Slack signals into reviewed LinkedIn drafts.

## What Runs

- Frontend: React + Vite
- API: FastAPI
- Database: PostgreSQL 16 with pgvector
- Queue/cache: Redis
- Background jobs: Celery worker
- Scheduler: Celery Beat

Vesper does not require Stripe, a licence key, or a Vesper subscription.

## Quick Start

1. Copy environment variables.

```bash
cp .env.example .env
```

2. Generate `APP_SECRET_KEY` and paste it into `.env`.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

3. Fill in OAuth and API credentials in `.env`.

Required for the full app:

- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET`
- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
- `OPENAI_API_KEY`

4. Start everything with Docker.

```bash
docker compose up --build
```

5. Apply database migrations.

```bash
docker compose exec backend alembic upgrade head
```

6. Open the app.

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## OAuth Redirect URLs

For local Docker setup, register these callback URLs:

- Google: `http://localhost:8000/api/auth/google/callback`
- Slack: `http://localhost:8000/api/oauth/slack/callback`
- LinkedIn: `http://localhost:8000/api/oauth/linkedin/callback`
- Slack interactivity: `http://localhost:8000/api/webhooks/slack/actions`

## Processes

The Docker Compose stack starts:

- `db`: pgvector Postgres
- `redis`: Redis broker/cache
- `backend`: FastAPI API
- `worker`: Celery queues `draft_pipeline,intake,publishing,maintenance`
- `beat`: scheduled scans, token refresh, cleanup, due-post dispatch
- `frontend`: static Vite build served by nginx

## Manual Development

Backend:

```bash
cd backend
python -m venv venv
source venv/Scripts/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Worker:

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info -Q draft_pipeline,intake,publishing,maintenance
```

Beat:

```bash
cd backend
celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```
