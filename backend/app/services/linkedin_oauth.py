"""LinkedIn OAuth service: install URL, code exchange, workspace token upsert.

Flow:
  1. build_install_url(state)                   → browser redirect URL
  2. exchange_code(code)                        → LinkedInInstallData (access + refresh tokens)
  3. upsert_tokens(db, workspace, user_id, data)→ create-or-update two OAuthToken rows
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crypto import encrypt
from app.models.audit_log import AuditLog
from app.models.oauth_token import OAuthToken
from app.models.workspace import Workspace

_LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Scopes available on Default + Standard tiers (no Marketing Developer Platform required)
# openid/profile/email — identity at install time (OpenID Connect)
# w_member_social       — post to personal profile (Share on LinkedIn)
_SCOPES = "openid profile email w_member_social"

# Fallback expiry values when LinkedIn omits them in the response body
_DEFAULT_ACCESS_EXPIRES_SECONDS = 5_183_944   # ~60 days
_DEFAULT_REFRESH_EXPIRES_SECONDS = 31_536_000  # ~365 days


class LinkedInOAuthError(Exception):
    """Raised when LinkedIn's token endpoint returns an error or missing fields."""


@dataclass(frozen=True)
class LinkedInInstallData:
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    scopes: str


def build_install_url(state: str) -> str:
    """Return the LinkedIn OAuth 2.0 authorization URL for browser redirect."""
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": f"{settings.app_base_url}/api/oauth/linkedin/callback",
        "scope": _SCOPES,
        "state": state,
    }
    return f"{_LINKEDIN_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> LinkedInInstallData:
    """Exchange a LinkedIn authorization code for access + refresh tokens.

    Raises LinkedInOAuthError if the response is missing the access_token field.
    Raises httpx.HTTPStatusError on non-2xx HTTP response.
    """
    now = datetime.now(tz=timezone.utc)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
                "redirect_uri": f"{settings.app_base_url}/api/oauth/linkedin/callback",
            },
        )
        resp.raise_for_status()

    body = resp.json()
    if "access_token" not in body:
        raise LinkedInOAuthError(body.get("error", "missing_access_token"))

    access_expires_in: int = body.get("expires_in", _DEFAULT_ACCESS_EXPIRES_SECONDS)
    refresh_expires_in: int = body.get(
        "refresh_token_expires_in", _DEFAULT_REFRESH_EXPIRES_SECONDS
    )

    return LinkedInInstallData(
        access_token=body["access_token"],
        access_token_expires_at=now + timedelta(seconds=access_expires_in),
        refresh_token=body.get("refresh_token", ""),
        refresh_token_expires_at=now + timedelta(seconds=refresh_expires_in),
        scopes=body.get("scope", _SCOPES),
    )


async def upsert_tokens(
    db: AsyncSession,
    workspace: Workspace,
    user_id: UUID,
    data: LinkedInInstallData,
) -> None:
    """Encrypt and store LinkedIn access + refresh tokens for the workspace.

    - Inserts or updates two OAuthToken rows: token_type='access' and 'refresh'.
    - Both rows use provider='linkedin_company' and user_id=NULL (workspace-level).
    - Advances workspace.onboarding_step from 'connect_linkedin' → 'channels_setup'.
    - Writes an AuditLog entry for the connection event.
    """
    token_rows = (
        ("access", data.access_token, data.access_token_expires_at),
        ("refresh", data.refresh_token, data.refresh_token_expires_at),
    )
    for token_type, raw_token, expires_at in token_rows:
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.workspace_id == workspace.id,
                OAuthToken.provider == "linkedin_company",
                OAuthToken.token_type == token_type,
                OAuthToken.user_id == None,  # noqa: E711 — SQLAlchemy IS NULL comparison
            )
        )
        existing = result.scalar_one_or_none()
        encrypted = encrypt(raw_token)

        if existing is None:
            db.add(
                OAuthToken(
                    workspace_id=workspace.id,
                    provider="linkedin_company",
                    token_type=token_type,
                    encrypted_token=encrypted.ciphertext,
                    nonce=encrypted.nonce,
                    tag=encrypted.tag,
                    scopes=data.scopes,
                    expires_at=expires_at,
                )
            )
        else:
            existing.encrypted_token = encrypted.ciphertext
            existing.nonce = encrypted.nonce
            existing.tag = encrypted.tag
            existing.scopes = data.scopes
            existing.expires_at = expires_at

    if workspace.onboarding_step == "connect_linkedin":
        workspace.onboarding_step = "channels_setup"

    db.add(
        AuditLog(
            workspace_id=workspace.id,
            entity_type="oauth_token",
            entity_id=workspace.id,
            action="linkedin_connected",
            actor=str(user_id),
        )
    )

    await db.flush()


async def refresh_token_for_workspace(
    db: AsyncSession,
    refresh_token_row: OAuthToken,
) -> bool:
    """Refresh the LinkedIn access token for one workspace using its stored refresh token.

    Queries the corresponding access token row, calls LinkedIn's token refresh endpoint,
    and updates both rows in place.

    Returns True on success, False on failure (caller writes the audit entry).
    Raises nothing — all errors are caught and returned as False.
    """
    from app.crypto import EncryptedToken, decrypt  # local to avoid circular import

    try:
        raw_refresh = decrypt(
            EncryptedToken(
                ciphertext=refresh_token_row.encrypted_token,
                nonce=refresh_token_row.nonce,
                tag=refresh_token_row.tag,
            )
        )
    except Exception:
        return False

    now = datetime.now(tz=timezone.utc)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _LINKEDIN_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": raw_refresh,
                    "client_id": settings.linkedin_client_id,
                    "client_secret": settings.linkedin_client_secret,
                },
            )
            resp.raise_for_status()
        body = resp.json()
    except Exception:
        return False

    if "access_token" not in body:
        return False

    access_expires_in: int = body.get("expires_in", _DEFAULT_ACCESS_EXPIRES_SECONDS)
    refresh_expires_in: int = body.get(
        "refresh_token_expires_in", _DEFAULT_REFRESH_EXPIRES_SECONDS
    )
    new_refresh_token: str = body.get("refresh_token", raw_refresh)

    # Update access token row
    access_result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.workspace_id == refresh_token_row.workspace_id,
            OAuthToken.provider == "linkedin_company",
            OAuthToken.token_type == "access",
            OAuthToken.user_id == None,  # noqa: E711
        )
    )
    access_row = access_result.scalar_one_or_none()
    if access_row is not None:
        new_access = encrypt(body["access_token"])
        access_row.encrypted_token = new_access.ciphertext
        access_row.nonce = new_access.nonce
        access_row.tag = new_access.tag
        access_row.expires_at = now + timedelta(seconds=access_expires_in)

    # Update refresh token row
    new_refresh_encrypted = encrypt(new_refresh_token)
    refresh_token_row.encrypted_token = new_refresh_encrypted.ciphertext
    refresh_token_row.nonce = new_refresh_encrypted.nonce
    refresh_token_row.tag = new_refresh_encrypted.tag
    refresh_token_row.expires_at = now + timedelta(seconds=refresh_expires_in)

    await db.flush()
    return True
