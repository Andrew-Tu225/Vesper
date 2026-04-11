"""Google OAuth routes: login, callback, logout, and current-user endpoint."""

import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SESSION_PREFIX, SESSION_TTL
from app.config import settings
from app.database import get_db
from app.redis import get_redis
from app.services.google_auth import build_auth_url, exchange_code, upsert_user

router = APIRouter(prefix="/google", tags=["auth-google"])

_STATE_PREFIX = "google_oauth_state:"
_STATE_TTL = 600  # 10 minutes


@router.get("/login")
async def google_login(
    redis: Redis = Depends(get_redis),
) -> RedirectResponse:
    """Generate a CSRF state token and redirect the browser to Google's consent screen."""
    state = os.urandom(32).hex()
    await redis.set(f"{_STATE_PREFIX}{state}", "1", ex=_STATE_TTL)
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
    4. Create a server-side session in Redis and set an HttpOnly cookie.
    5. Redirect to the frontend dashboard.
    """
    state_key = f"{_STATE_PREFIX}{state}"
    stored = await redis.get(state_key)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state"
        )
    await redis.delete(state_key)

    try:
        google_user = await exchange_code(code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Google authentication failed"
        )

    user = await upsert_user(db, google_user)

    session_id = os.urandom(32).hex()
    session_data = json.dumps({"user_id": str(user.id)})
    await redis.set(f"{SESSION_PREFIX}{session_id}", session_data, ex=SESSION_TTL)

    response = RedirectResponse(
        url=f"{settings.app_frontend_url}/dashboard",
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


