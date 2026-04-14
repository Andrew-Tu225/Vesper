"""LinkedIn OAuth routes: install (redirect to consent screen) and callback (exchange + store tokens)."""

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
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.redis import get_redis
from app.services.linkedin_oauth import (
    LinkedInOAuthError,
    build_install_url,
    exchange_code,
    upsert_tokens,
)

router = APIRouter(prefix="/linkedin", tags=["oauth-linkedin"])

_STATE_PREFIX = "linkedin_oauth_state:"
_STATE_TTL = 600  # 10 minutes


@router.get("/install")
async def linkedin_install(
    redis: Redis = Depends(get_redis),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    """Redirect the authenticated user to LinkedIn's OAuth consent screen.

    Stores the user_id in Redis (10-min TTL) so the callback can identify
    the user without relying on the session cookie being forwarded.
    """
    state = os.urandom(32).hex()
    await redis.set(f"{_STATE_PREFIX}{state}", str(user.id), ex=_STATE_TTL)
    return RedirectResponse(url=build_install_url(state), status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def linkedin_callback(
    state: str = Query(...),
    code: str = Query(default=""),
    error: str = Query(default=""),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle LinkedIn's redirect after the user approves (or denies) the consent screen.

    1. Redirect gracefully if the user denied access (?error=user_cancelled_login).
    2. Verify and consume the one-time CSRF state key (contains user_id).
    3. Load the authenticated user from the DB.
    4. Find the user's workspace (Slack OAuth must have run first to create it).
    5. Exchange the authorization code for access + refresh tokens.
    6. Upsert two encrypted OAuthToken rows and advance onboarding_step.
    7. Redirect to the next onboarding step.
    """
    # Handle user-denied before consuming the state key
    if error:
        return RedirectResponse(
            url=f"{settings.app_frontend_url}/onboarding?step=connect_linkedin&error=access_denied",
            status_code=status.HTTP_302_FOUND,
        )

    state_key = f"{_STATE_PREFIX}{state}"
    raw_user_id = await redis.get(state_key)
    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state"
        )
    await redis.delete(state_key)

    user_id_str = raw_user_id if isinstance(raw_user_id, str) else raw_user_id.decode()
    user_result = await db.execute(select(User).where(User.id == UUID(user_id_str)))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Slack OAuth must precede LinkedIn OAuth — workspace must already exist
    ws_result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.asc())
        .limit(1)
    )
    workspace = ws_result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workspace found — complete Slack OAuth first",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code"
        )

    try:
        install_data = await exchange_code(code)
    except (LinkedInOAuthError, Exception):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="LinkedIn authentication failed"
        )

    await upsert_tokens(db, workspace, user.id, install_data)

    return RedirectResponse(
        url=f"{settings.app_frontend_url}/onboarding?step=channels_setup",
        status_code=status.HTTP_302_FOUND,
    )
