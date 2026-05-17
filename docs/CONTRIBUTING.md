# Contributing to Vesper

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker and Docker Compose
- PostgreSQL 16 with pgvector, or the Docker Compose `db` service
- Redis 7, or the Docker Compose `redis` service

## Quick Start With Docker

1. Clone and configure.

```bash
git clone <repo>
cd Vesper
cp .env.example .env
```

2. Generate `APP_SECRET_KEY` and paste it into `.env`.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

3. Fill in the OAuth/API keys you need. See [ENV.md](ENV.md).

4. Start the stack.

```bash
docker compose up --build
```

5. Apply migrations.

```bash
docker compose exec backend alembic upgrade head
```

Services:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Manual Development

Start infrastructure:

```bash
docker compose up db redis -d
```

Backend:

```bash
cd backend
python -m venv venv
source venv/Scripts/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

PowerShell activation:

```powershell
.\venv\Scripts\Activate.ps1
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

Scheduler:

```bash
cd backend
celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```

## Available Commands

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | Start dev API server |
| `celery -A app.workers.celery_app worker --loglevel=info -Q draft_pipeline,intake,publishing,maintenance` | Start Celery worker |
| `celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule` | Start scheduled jobs |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Roll back one migration |
| `alembic revision --autogenerate -m "description"` | Generate a migration |
| `pytest` | Run backend tests with coverage |
| `ruff check .` | Lint Python code |
| `black --check .` | Check Python formatting |
| `mypy app` | Run backend type checks |
| `npm test` | Run frontend unit tests |
| `npm run build` | Type-check and build the frontend |

## Testing

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The backend coverage threshold is 80%.

Frontend:

```bash
cd frontend
npm test
npm run build
```

## Database Migrations

1. Modify or add a model in `backend/app/models/`.
2. Generate a migration: `alembic revision --autogenerate -m "short description"`.
3. Review the generated file in `backend/migrations/versions/`.
4. Apply it with `alembic upgrade head`.

Do not edit `001_initial_schema.py` after it has shipped. Add a new migration instead.

## Pull Request Checklist

- [ ] Backend tests pass where relevant.
- [ ] Frontend tests/build pass where relevant.
- [ ] Linting and formatting are clean for touched code.
- [ ] No secrets or credentials are committed.
- [ ] Migration included for schema changes.
