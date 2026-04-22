"""Slack OAuth routes: install (redirect to consent screen) and callback (exchange + store token)."""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.redis import get_redis
from app.services.slack_oauth import (
    build_install_url,
    exchange_code,
    upsert_workspace_and_token,
)

router = APIRouter(prefix="/slack", tags=["oauth-slack"])

_STATE_PREFIX = "slack_oauth_state:"
_STATE_TTL = 600  # 10 minutes


@router.get("/install")
async def slack_install(
    redis: Redis = Depends(get_redis),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    """Redirect the authenticated user to Slack's OAuth consent screen.

    Stores the user_id in the Redis state so the callback can identify
    the user without relying on the session cookie being forwarded.
    """
    state = os.urandom(32).hex()
    await redis.set(f"{_STATE_PREFIX}{state}", str(user.id), ex=_STATE_TTL)
    return RedirectResponse(url=build_install_url(state), status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def slack_callback(
    code: str = Query(...),
    state: str = Query(...),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Slack's redirect after the user installs the app.

    1. Verify and consume the one-time CSRF state (contains user_id).
    2. Load the authenticated user from the DB.
    3. Exchange the authorization code for a bot token.
    4. Upsert the Workspace and encrypted OAuthToken.
    5. Redirect to the next onboarding step.
    """
    state_key = f"{_STATE_PREFIX}{state}"
    raw_user_id = await redis.get(state_key)
    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state"
        )
    await redis.delete(state_key)

    user_id_str = raw_user_id if isinstance(raw_user_id, str) else raw_user_id.decode()
    result = await db.execute(select(User).where(User.id == UUID(user_id_str)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    try:
        install_data = await exchange_code(code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Slack authentication failed"
        )

    await upsert_workspace_and_token(db, user, install_data)

    return RedirectResponse(
        url=f"{settings.app_frontend_url}/dashboard",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/status")
async def slack_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return Slack connection status for the user's workspace."""
    ws_result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.asc())
        .limit(1)
    )
    workspace = ws_result.scalar_one_or_none()
    if workspace is None:
        return {"connected": False}

    token_result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.workspace_id == workspace.id,
            OAuthToken.provider == "slack",
            OAuthToken.token_type == "bot",
        )
    )
    if token_result.scalar_one_or_none() is None:
        return {"connected": False}

    channels: list = workspace.settings.get("enrichment_channels", [])
    return {
        "connected": True,
        "workspace_name": workspace.name,
        "channels_configured": len(channels) > 0,
        "channel_count": len(channels),
    }
