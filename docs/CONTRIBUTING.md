# Contributing to Vesper

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose
- PostgreSQL 16 with pgvector (or use Docker)
- Redis 7 (or use Docker)

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd vesper
cp .env.example .env
# Fill in all required values — see docs/ENV.md
```

### 2. Generate the encryption key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Paste result into APP_SECRET_KEY in .env
```

### 3. Start infrastructure

```bash
docker compose up db redis -d
```

### 4. Backend setup

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 5. Worker (separate terminal)

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info -Q draft_pipeline,intake,publishing,maintenance
```

### 6. Full stack via Docker

```bash
docker compose up
```

Services:
- Backend API: http://localhost:8000
- Frontend:    http://localhost:5173
- API docs:    http://localhost:8000/docs

## Available Commands

<!-- AUTO-GENERATED: backend commands -->
| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload` | Start dev API server with hot reload |
| `celery -A app.workers.celery_app worker --loglevel=info` | Start Celery worker |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Roll back one migration |
| `alembic revision --autogenerate -m "description"` | Generate a new migration |
| `pytest` | Run test suite with coverage |
| `ruff check .` | Lint Python code |
| `black .` | Format Python code |
| `mypy app` | Run static type checker |
<!-- AUTO-GENERATED END -->

## Testing

```bash
cd backend
pytest                          # Run all tests (requires 80% coverage)
pytest -k "test_health"         # Run a specific test
pytest --cov=app --cov-report=html  # HTML coverage report
```

Coverage threshold is enforced at **80%** — the build will fail below this.

Test categories via `pytest.mark`:
- `@pytest.mark.unit` — pure logic, no I/O
- `@pytest.mark.integration` — hits real DB or Redis

## Code Style

All Python code must pass:

```bash
ruff check .          # linting (E, F, I, UP, B, S rules)
black --check .       # formatting
mypy app              # strict type checking
```

Line length: **100** characters. Python target: **3.12**.

## Database Migrations

1. Modify or add a model in `backend/app/models/`
2. Generate the migration: `alembic revision --autogenerate -m "short description"`
3. Review the generated file in `backend/migrations/versions/`
4. Apply: `alembic upgrade head`

Never edit the `001_initial_schema.py` file directly.

## Pull Request Checklist

- [ ] Tests written and passing (`pytest`)
- [ ] Coverage stays ≥ 80%
- [ ] Linting clean (`ruff check .`, `black --check .`)
- [ ] Types pass (`mypy app`)
- [ ] No secrets or credentials in code
- [ ] Migration included if schema changed
