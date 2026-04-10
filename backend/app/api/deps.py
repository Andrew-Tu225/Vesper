"""Shared FastAPI dependencies used across multiple routers."""

import hashlib
import hmac
import json
import time
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.redis import get_redis

_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes

# Session constants — also imported by app.api.auth.google
SESSION_PREFIX = "session:"
SESSION_TTL = 86400  # 24 hours


async def verify_slack_signature(
    request: Request,
    x_slack_request_timestamp: str = Header(...),
    x_slack_signature: str = Header(...),
) -> None:
    """
    FastAPI dependency that verifies Slack's request signature.

    Apply per-route (not globally) on every endpoint that receives Slack events
    or interactivity payloads.

    Raises HTTP 401 if the signature is missing, stale, or invalid.
    """
    now = int(time.time())
    try:
        timestamp = int(x_slack_request_timestamp)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid timestamp")

    if abs(now - timestamp) > _TIMESTAMP_TOLERANCE_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request timestamp too old")

    body = await request.body()
    basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

    expected = (
        "v0="
        + hmac.new(
            settings.slack_signing_secret.encode(),
            basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected, x_slack_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    vesper_session: str | None = Cookie(default=None),
):
    """Resolve the authenticated User from the session cookie.

    Reads the 'vesper_session' cookie, looks up the session in Redis,
    then loads the corresponding User from the database.

    Raises HTTP 401 if the cookie is missing, the session has expired,
    or the user no longer exists.
    """
    from app.models.user import User  # local import avoids circular dependency at module load

    if not vesper_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    raw = await redis.get(f"{SESSION_PREFIX}{vesper_session}")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )

    data = json.loads(raw)
    user_id = UUID(data["user_id"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user
