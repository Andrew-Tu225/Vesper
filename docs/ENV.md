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
| `SLACK_CLIENT_ID` | Yes | OAuth app client ID | Slack app dashboard → Basic Information |
| `SLACK_CLIENT_SECRET` | Yes | OAuth app client secret | Slack app dashboard → Basic Information |
| `SLACK_SIGNING_SECRET` | Yes | Used to verify webhook request signatures | Slack app dashboard → Basic Information |

Redirect URI to register in Slack app settings → OAuth & Permissions:
```
{APP_BASE_URL}/api/oauth/slack/callback
```

## Google / Gmail

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID | Google Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret | Google Cloud Console → APIs & Services → Credentials |

Redirect URI to register in Google Cloud Console → Credentials → Authorized redirect URIs:
```
{APP_BASE_URL}/api/auth/google/callback
```

Required OAuth scopes: `openid email profile`

## LinkedIn

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `LINKEDIN_CLIENT_ID` | Yes | LinkedIn app client ID | LinkedIn Developer Portal → app → Auth tab |
| `LINKEDIN_CLIENT_SECRET` | Yes | LinkedIn app primary client secret | LinkedIn Developer Portal → app → Auth tab |

Redirect URI to register in LinkedIn Developer Portal → app → Auth → Authorized redirect URLs:
```
{APP_BASE_URL}/api/oauth/linkedin/callback
```

Required LinkedIn app products (add under the Products tab):
- **Sign In with LinkedIn using OpenID Connect** — unlocks `openid profile email` (auto-approved)
- **Share on LinkedIn** — unlocks `w_member_social` (auto-approved)
- **Advertising API** — unlocks `r_organization_social` + `w_organization_social` for company-page posting (requires LinkedIn review, 1–3 days)

Scopes currently used: `openid profile email w_member_social` — update `_SCOPES` in `backend/app/services/linkedin_oauth.py` once `Advertising API` is approved to add `r_organization_social w_organization_social`.

## OpenAI / OpenRouter

Vesper uses OpenRouter during development and can switch to direct OpenAI in production by
changing only `.env` — no code change required. OpenRouter takes precedence when
`OPENROUTER_API_KEY` is set.

| Variable | Required | Description | Where to get it |
|----------|----------|-------------|-----------------|
| `OPENAI_API_KEY` | Production only | Direct OpenAI API key — used when `OPENROUTER_API_KEY` is not set | platform.openai.com → API keys |
| `OPENROUTER_API_KEY` | Dev / optional | OpenRouter key — takes precedence over `OPENAI_API_KEY` when set | openrouter.ai → Keys |
| `OPENROUTER_BASE_URL` | No | OpenRouter API base URL. Default: `https://openrouter.ai/api/v1` | — |
| `MODEL_CLASSIFY` | No | Model used for classification, redaction, and enrichment. Default: `openai/gpt-4o-mini` | — |
| `MODEL_GENERATE` | No | Model used for LinkedIn draft generation. Default: `openai/gpt-4o` | — |

Model name format differs per provider: OpenRouter uses `openai/gpt-4o-mini`; direct OpenAI uses `gpt-4o-mini`.
Update `MODEL_CLASSIFY` and `MODEL_GENERATE` when switching providers.

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
