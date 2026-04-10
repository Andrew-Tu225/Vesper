"""Google OAuth service: auth URL construction, code exchange, and user upsert.

Flow:
  1. build_auth_url(state)  → redirect URL for the browser
  2. exchange_code(code)    → GoogleUserInfo (verifies id_token with Google's public certs)
  3. upsert_user(db, info)  → create-or-update User row, return the User
"""

import asyncio
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SCOPES = "openid email profile"


@dataclass(frozen=True)
class GoogleUserInfo:
    google_id: str
    email: str
    display_name: str | None
    avatar_url: str | None


def build_auth_url(state: str) -> str:
    """Return the Google authorization URL the browser should be redirected to."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.app_base_url}/api/auth/google/callback",
        "response_type": "code",
        "scope": _SCOPES,
        "state": state,
    }
    return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> GoogleUserInfo:
    """Exchange an authorization code for a verified GoogleUserInfo.

    Steps:
      - POST to Google's token endpoint to get an id_token
      - Verify the id_token signature using Google's public certs (cached after first fetch)
      - Return a typed GoogleUserInfo dataclass

    Raises httpx.HTTPStatusError if the token endpoint returns a non-2xx status.
    Raises google.auth.exceptions.GoogleAuthError if id_token verification fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{settings.app_base_url}/api/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()

    raw_id_token: str = resp.json()["id_token"]

    # verify_oauth2_token uses the `requests` library (sync) to fetch Google's
    # public certs. Certs are cached in memory after the first call.
    # Wrapping in to_thread keeps the async event loop free during the fetch.
    def _verify() -> dict:
        return id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.google_client_id,
        )

    id_info: dict = await asyncio.to_thread(_verify)

    return GoogleUserInfo(
        google_id=id_info["sub"],
        email=id_info["email"],
        display_name=id_info.get("name"),
        avatar_url=id_info.get("picture"),
    )


async def upsert_user(db: AsyncSession, info: GoogleUserInfo) -> User:
    """Create a new User or update an existing one, keyed by google_id.

    Fallback: if no row matches google_id but the email exists, we re-link it
    (handles the rare case where Google rotates a user's sub).
    """
    result = await db.execute(select(User).where(User.google_id == info.google_id))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == info.email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=info.email,
            google_id=info.google_id,
            display_name=info.display_name,
            avatar_url=info.avatar_url,
        )
        db.add(user)
    else:
        user.google_id = info.google_id
        user.display_name = info.display_name
        user.avatar_url = info.avatar_url

    # Flush to assign a PK without committing — get_db commits on success.
    await db.flush()
    return user
