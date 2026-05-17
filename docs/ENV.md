# Environment Variables

Copy `.env.example` to `.env` at the repo root and fill in the values for the integrations you want to run.

The backend loads both `../.env` and `backend/.env`, so the root `.env` works for Docker Compose and manual backend development from `backend/`.

## Database

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `POSTGRES_USER` | Yes | PostgreSQL username used by Docker Compose | `vesper` |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password used by Docker Compose | `changeme` |
| `POSTGRES_DB` | Yes | PostgreSQL database name | `vesper` |
| `DATABASE_URL` | Yes | Async SQLAlchemy connection string | `postgresql+asyncpg://vesper:changeme@localhost:5433/vesper` |

Notes:
- Docker Compose exposes Postgres on host port `5433`.
- Compose services override `DATABASE_URL` internally to use `db:5432`.
- The database image is `pgvector/pgvector:pg16`; migrations create the `vector` and `uuid-ossp` extensions.

## Redis / Worker

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `REDIS_URL` | Yes | Redis URL for sessions, OAuth state, Celery broker/results, and dedupe keys | `redis://localhost:6379/0` |

## Slack

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_CLIENT_ID` | For Slack OAuth | Slack app client ID |
| `SLACK_CLIENT_SECRET` | For Slack OAuth | Slack app client secret |
| `SLACK_SIGNING_SECRET` | For Slack actions | Verifies Slack interactivity signatures |

Register these URLs in the Slack app:

```text
{APP_BASE_URL}/api/oauth/slack/callback
{APP_BASE_URL}/api/webhooks/slack/actions
```

Slack approval cards use interactive buttons and modals. In the Slack app
dashboard, enable Interactivity under **Interactivity & Shortcuts** and set the
Request URL to:

```
{APP_BASE_URL}/api/webhooks/slack/actions
```

For local development, `APP_BASE_URL` must be a public HTTPS tunnel URL such as
ngrok or Cloudflare Tunnel. Slack cannot call `localhost`, and button clicks will
show "This app isn't configured to be interactive" when Interactivity is disabled
or the Request URL is missing.

Required bot scopes:

```text
channels:history,channels:read,groups:history,groups:read,chat:write,commands
```

## Google

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | For login | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | For login | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Optional | Override for the Google callback URL |

Register this redirect URI:

```text
{APP_BASE_URL}/api/auth/google/callback
```

Required scopes:

```text
openid email profile
```

## LinkedIn

| Variable | Required | Description |
|----------|----------|-------------|
| `LINKEDIN_CLIENT_ID` | For LinkedIn OAuth | LinkedIn app client ID |
| `LINKEDIN_CLIENT_SECRET` | For LinkedIn OAuth | LinkedIn app client secret |

Register this redirect URI:

```text
{APP_BASE_URL}/api/oauth/linkedin/callback
```

Current scopes:

```text
openid profile email w_member_social
```

Required LinkedIn products:

- Sign In with LinkedIn using OpenID Connect
- Share on LinkedIn

## OpenAI

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | For AI classification, embeddings, enrichment, and generation | OpenAI API key | none |
| `MODEL_CLASSIFY` | No | Model used for classification and enrichment | `gpt-4o-mini` |
| `MODEL_GENERATE` | No | Model used for draft generation and rewrite | `gpt-4o` |

## App

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `APP_SECRET_KEY` | Yes | 64-character hex string used for AES-256-GCM token encryption | generated value |
| `APP_BASE_URL` | Yes | Public backend base URL used for OAuth redirects | `http://localhost:8000` |
| `APP_FRONTEND_URL` | Yes | Public frontend base URL used after OAuth callbacks | `http://localhost:5173` |
| `APP_ENV` | No | `development` or `production`; production sets secure auth cookies | `development` |

Generate `APP_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Frontend

Frontend-only values live in `frontend/.env` when running `npm run dev`.

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `VITE_API_PROXY_TARGET` | No | Backend target for the Vite `/api` dev proxy | `http://localhost:8000` |
| `RESEND_API_KEY` | Optional | Resend API key for the waitlist edge function | none |
| `RESEND_AUDIENCE_ID` | Optional | Resend audience ID for the waitlist edge function | none |

The browser app always uses relative `/api` URLs so the `vesper_session` cookie works through Vite, nginx, or any reverse proxy.

## Not Required

Vesper no longer requires Stripe, a licence key, or any subscription/payment variables.
