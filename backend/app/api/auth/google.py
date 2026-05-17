"""Google OAuth routes: login, callback, logout, and current-user endpoint."""

import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SESSION_PREFIX, SESSION_TTL
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.redis import get_redis
from app.services.google_auth import build_auth_url, exchange_code, upsert_user

router = APIRouter(prefix="/google", tags=["auth-google"])

_STATE_PREFIX = "google_oauth_state:"
_STATE_TTL = 600  # 10 minutes

# Paths a caller may request as the post-login destination.
_ALLOWED_NEXT_PATHS = frozenset({
    "/dashboard",
    "/settings",
    "/queue",
    "/calendar",
})


@router.get("/login")
async def google_login(
    next: str | None = Query(None, alias="next"),
    redis: Redis = Depends(get_redis),
) -> RedirectResponse:
    """Generate a CSRF state token and redirect the browser to Google's consent screen.

    Accepts an optional ``?next=<path>`` parameter (allowlisted) that controls
    where the user lands after a successful OAuth round-trip.  Defaults to
    ``/onboarding`` so new users arrive at the connect-Slack step.
    """
    next_path = next if next in _ALLOWED_NEXT_PATHS else "/dashboard"
    state = os.urandom(32).hex()
    state_value = json.dumps({"next": next_path})
    await redis.set(f"{_STATE_PREFIX}{state}", state_value, ex=_STATE_TTL)
    return RedirectResponse(url=build_auth_url(state), status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Google's redirect after the user consents.

    1. Verify and consume the one-time CSRF state.
    2. Exchange the authorization code for a verified Google identity.
    3. Upsert the User row.
    4. Ensure the user has a workspace.
    5. Create a server-side session in Redis and set an HttpOnly cookie.
    6. Redirect to the path stored in the OAuth state (default: /onboarding).
    """
    state_key = f"{_STATE_PREFIX}{state}"
    stored = await redis.get(state_key)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state"
        )
    await redis.delete(state_key)

    raw = stored.decode() if isinstance(stored, bytes) else stored
    try:
        state_data = json.loads(raw)
        next_path = state_data.get("next", "/dashboard")
    except (ValueError, AttributeError):
        next_path = "/onboarding"

    try:
        google_user = await exchange_code(code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Google authentication failed"
        )

    user = await upsert_user(db, google_user)
    await _ensure_workspace(user, db)

    session_id = os.urandom(32).hex()
    session_data = json.dumps({"user_id": str(user.id)})
    await redis.set(f"{SESSION_PREFIX}{session_id}", session_data, ex=SESSION_TTL)

    response = RedirectResponse(
        url=f"{settings.app_frontend_url}{next_path}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key="vesper_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=SESSION_TTL,
    )
    return response


async def _ensure_workspace(user: User, db: AsyncSession) -> None:
    """Create a workspace for a user who has none.

    Runs after every Google sign-in so that users who signed up via the
    landing-page CTA (before connecting Slack) get a workspace immediately,
    allowing the rest of the app to function without a 400 error.
    """
    existing = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return

    display = (user.display_name or user.email.split("@")[0]).replace(".", " ")
    workspace = Workspace(
        name=f"{display}'s workspace",
        owner_user_id=user.id,
    )
    db.add(workspace)
    await db.flush()

    db.add(WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    ))
    await db.commit()


@router.post("/logout")
async def google_logout(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """Delete the server-side session and clear the browser cookie."""
    session_id = request.cookies.get("vesper_session")
    if session_id:
        await redis.delete(f"{SESSION_PREFIX}{session_id}")
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(
        key="vesper_session",
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    return response
