# Environment Variables

Copy `.env.example` to `.env` and fill in all required values before running the app.

<!-- AUTO-GENERATED from .env.example -->
## Database

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `POSTGRES_USER` | Yes | PostgreSQL username | `vesper` |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password | `changeme` |
| `POSTGRES_DB` | Yes | Database name | `vesper` |
| `DATABASE_URL` | Yes | Full async connection string — uses the three vars above | `postgresql+asyncpg://user:pass@localhost:5432/vesper` |

## Redis / Worker

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `REDIS_URL` | Yes | Redis connection string used by Celery and the app | `redis://localhost:6379/0` |

## Slack

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `SLACK_CLIENT_ID` | Yes (Phase 2) | OAuth app client ID | Slack app dashboard → Basic Information |
| `SLACK_CLIENT_SECRET` | Yes (Phase 2) | OAuth app client secret | Slack app dashboard → Basic Information |
| `SLACK_SIGNING_SECRET` | Yes (Phase 2) | Used to verify webhook request signatures | Slack app dashboard → Basic Information |

## Google / Gmail

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `GOOGLE_CLIENT_ID` | Yes (Phase 3) | Google OAuth client ID | Google Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | Yes (Phase 3) | Google OAuth client secret | Google Cloud Console → APIs & Services → Credentials |

## LinkedIn

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `LINKEDIN_CLIENT_ID` | Yes (Phase 5) | LinkedIn app client ID | LinkedIn Developer Portal |
| `LINKEDIN_CLIENT_SECRET` | Yes (Phase 5) | LinkedIn app client secret | LinkedIn Developer Portal |

## OpenAI

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `OPENAI_API_KEY` | Yes (Phase 2) | API key for classification, embedding, and generation | platform.openai.com → API keys |

## App

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `APP_SECRET_KEY` | Yes | 64-character hex string (32 random bytes) for AES-256-GCM token encryption. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | `a3f1...` (64 hex chars) |
| `APP_BASE_URL` | Yes | Public base URL of the backend — used for OAuth redirect URIs | `http://localhost:8000` |
| `APP_ENV` | No | Runtime environment. Controls debug behaviour. Default: `development` | `development` \| `production` |
<!-- AUTO-GENERATED END -->

## Notes

- `DATABASE_URL` in `.env` uses `localhost` for local dev. In `docker-compose.yml` it is overridden to point at the `db` service hostname.
- `APP_SECRET_KEY` must **never** be committed to version control. It protects all OAuth tokens stored in the database.
- Slack, Google, LinkedIn, and OpenAI variables are only required when the corresponding integration phase is active.
