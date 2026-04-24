"""Slack OAuth service: install URL, code exchange, workspace and token upsert.

Flow:
  1. build_install_url(state)              → redirect URL for the browser
  2. exchange_code(code)                   → SlackInstallData (bot token + team info)
  3. upsert_workspace_and_token(db, user, data) → create-or-update Workspace + OAuthToken
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import encrypt
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

_SLACK_AUTH_URL = "https://slack.com/oauth/v2/authorize"
_SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"

# Bot scopes required for Phase 2: channel monitoring + approval card posting
_BOT_SCOPES = "channels:history,channels:read,groups:history,groups:read,chat:write,commands"


class SlackOAuthError(Exception):
    """Raised when Slack's token endpoint returns ok=false."""


@dataclass(frozen=True)
class SlackInstallData:
    team_id: str
    team_name: str
    bot_token: str   # xoxb-...
    bot_scopes: str  # comma-separated granted scopes


def build_install_url(state: str) -> str:
    """Return the Slack OAuth V2 authorization URL the browser should be redirected to."""
    params = {
        "client_id": settings.slack_client_id,
        "scope": _BOT_SCOPES,
        "redirect_uri": f"{settings.app_base_url}/api/oauth/slack/callback",
        "state": state,
    }
    return f"{_SLACK_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> SlackInstallData:
    """Exchange a Slack OAuth authorization code for a bot token.

    Raises SlackOAuthError if Slack returns ok=false (e.g. invalid_code).
    Raises httpx.HTTPStatusError on a non-2xx HTTP response.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _SLACK_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "redirect_uri": f"{settings.app_base_url}/api/oauth/slack/callback",
            },
        )
        resp.raise_for_status()

    body = resp.json()
    if not body.get("ok"):
        raise SlackOAuthError(body.get("error", "unknown_error"))

    return SlackInstallData(
        team_id=body["team"]["id"],
        team_name=body["team"]["name"],
        bot_token=body["access_token"],
        bot_scopes=body.get("scope", ""),
    )


async def upsert_workspace_and_token(
    db: AsyncSession,
    user: User,
    data: SlackInstallData,
) -> Workspace:
    """Create or update the Workspace and its Slack bot OAuthToken.

    - Creates a new Workspace if none exists for data.team_id.
    - Ensures user is a member of the workspace (inserts if missing).
    - Inserts or updates the encrypted Slack bot token row.
    - Advances onboarding_step from 'connect_slack' → 'connect_linkedin'.
    """
    # --- workspace ---
    result = await db.execute(
        select(Workspace).where(Workspace.slack_team_id == data.team_id)
    )
    workspace = result.scalar_one_or_none()

    if workspace is None:
        workspace = Workspace(
            name=data.team_name,
            owner_user_id=user.id,
            slack_team_id=data.team_id,
            trial_ends_at=datetime.now(tz=timezone.utc) + timedelta(days=30),
        )
        db.add(workspace)
        await db.flush()  # populate workspace.id before FK references below

    if workspace.onboarding_step == "connect_slack":
        workspace.onboarding_step = "connect_linkedin"

    # --- workspace_member ---
    member_result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if member_result.scalar_one_or_none() is None:
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role="member",
            )
        )

    # --- oauth_token (insert or update) ---
    token_result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.workspace_id == workspace.id,
            OAuthToken.provider == "slack",
            OAuthToken.token_type == "bot",
            OAuthToken.user_id == None,  # noqa: E711 — SQLAlchemy IS NULL comparison
        )
    )
    existing_token = token_result.scalar_one_or_none()
    encrypted = encrypt(data.bot_token)

    if existing_token is None:
        db.add(
            OAuthToken(
                workspace_id=workspace.id,
                provider="slack",
                token_type="bot",
                encrypted_token=encrypted.ciphertext,
                nonce=encrypted.nonce,
                tag=encrypted.tag,
                scopes=data.bot_scopes,
            )
        )
    else:
        existing_token.encrypted_token = encrypted.ciphertext
        existing_token.nonce = encrypted.nonce
        existing_token.tag = encrypted.tag
        existing_token.scopes = data.bot_scopes

    await db.flush()
    return workspace
