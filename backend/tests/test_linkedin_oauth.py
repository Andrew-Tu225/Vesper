"""Tests for LinkedIn OAuth routes and service functions."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.models.workspace import Workspace
from app.services.linkedin_oauth import (
    LinkedInInstallData,
    LinkedInOAuthError,
    build_install_url,
    upsert_tokens,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_user(**kwargs) -> User:
    return User(
        id=kwargs.get("id", uuid4()),
        email=kwargs.get("email", "user@example.com"),
        google_id=kwargs.get("google_id", "google-sub-456"),
        display_name=kwargs.get("display_name", "Test User"),
        avatar_url=None,
    )


def _make_workspace(**kwargs) -> Workspace:
    return Workspace(
        id=kwargs.get("id", uuid4()),
        name=kwargs.get("name", "Acme Corp"),
        owner_user_id=kwargs.get("owner_user_id", uuid4()),
        slack_team_id=kwargs.get("slack_team_id", "T123456"),
        onboarding_step=kwargs.get("onboarding_step", "connect_linkedin"),
    )


def _make_install_data(**kwargs) -> LinkedInInstallData:
    now = datetime.now(tz=timezone.utc)
    return LinkedInInstallData(
        access_token=kwargs.get("access_token", "li-access-token"),
        access_token_expires_at=kwargs.get(
            "access_token_expires_at", now + timedelta(days=60)
        ),
        refresh_token=kwargs.get("refresh_token", "li-refresh-token"),
        refresh_token_expires_at=kwargs.get(
            "refresh_token_expires_at", now + timedelta(days=365)
        ),
        scopes=kwargs.get("scopes", "openid profile email w_organization_social"),
    )


def _seed_session(mock_redis: AsyncMock, mock_db: AsyncMock, user: User) -> str:
    """Seed mock_redis with a valid session and mock_db to return the user."""
    session_id = "test-session-id"
    session_data = json.dumps({"user_id": str(user.id)})
    mock_redis.get = AsyncMock(return_value=session_data)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    return session_id


# ── build_install_url (service) ───────────────────────────────────────────────


def test_build_install_url_contains_required_params():
    url = build_install_url("test-state-xyz")

    assert "linkedin.com/oauth/v2/authorization" in url
    assert "response_type=code" in url
    assert "state=test-state-xyz" in url
    assert "redirect_uri=" in url
    assert "scope=" in url


def test_build_install_url_contains_posting_scopes():
    url = build_install_url("s")

    assert "w_organization_social" in url


def test_build_install_url_contains_client_id():
    from app.config import settings

    url = build_install_url("s")

    assert f"client_id={settings.linkedin_client_id}" in url


# ── GET /api/oauth/linkedin/install ──────────────────────────────────────────


async def test_install_requires_auth(client):
    resp = await client.get("/api/oauth/linkedin/install", follow_redirects=False)

    assert resp.status_code == 401


async def test_install_redirects_to_linkedin(client, mock_redis, mock_db):
    user = _make_user()
    _seed_session(mock_redis, mock_db, user)

    resp = await client.get(
        "/api/oauth/linkedin/install",
        cookies={"vesper_session": "test-session-id"},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "linkedin.com/oauth/v2/authorization" in location
    assert "state=" in location
    assert "scope=" in location


async def test_install_stores_user_id_in_redis(client, mock_redis, mock_db):
    user = _make_user()
    _seed_session(mock_redis, mock_db, user)

    await client.get(
        "/api/oauth/linkedin/install",
        cookies={"vesper_session": "test-session-id"},
        follow_redirects=False,
    )

    set_calls = [
        c for c in mock_redis.set.call_args_list if "linkedin_oauth_state:" in c[0][0]
    ]
    assert len(set_calls) == 1
    key, value = set_calls[0][0]
    assert key.startswith("linkedin_oauth_state:")
    assert value == str(user.id)
    assert set_calls[0][1]["ex"] == 600


# ── GET /api/oauth/linkedin/callback ─────────────────────────────────────────


async def test_callback_user_denied_redirects_gracefully(client, mock_redis):
    resp = await client.get(
        "/api/oauth/linkedin/callback?state=s&error=user_cancelled_login",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert "access_denied" in resp.headers["location"]
    assert "connect_linkedin" in resp.headers["location"]


async def test_callback_invalid_state_returns_400(client, mock_redis):
    mock_redis.get = AsyncMock(return_value=None)

    resp = await client.get(
        "/api/oauth/linkedin/callback?code=abc&state=stale", follow_redirects=False
    )

    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


async def test_callback_user_not_found_returns_401(client, mock_redis, mock_db):
    mock_redis.get = AsyncMock(return_value=str(uuid4()))

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get(
        "/api/oauth/linkedin/callback?code=code&state=s", follow_redirects=False
    )

    assert resp.status_code == 401


async def test_callback_no_workspace_returns_400(client, mock_redis, mock_db):
    user = _make_user()
    mock_redis.get = AsyncMock(return_value=str(user.id))

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    # workspace query returns None (no workspace yet)
    ws_result = MagicMock()
    ws_result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[user_result, ws_result])

    resp = await client.get(
        "/api/oauth/linkedin/callback?code=code&state=s", follow_redirects=False
    )

    assert resp.status_code == 400
    assert "slack" in resp.json()["detail"].lower()


async def test_callback_linkedin_api_error_returns_502(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace(owner_user_id=user.id)
    mock_redis.get = AsyncMock(return_value=str(user.id))

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    ws_result = MagicMock()
    ws_result.scalar_one_or_none.return_value = workspace
    mock_db.execute = AsyncMock(side_effect=[user_result, ws_result])

    with patch(
        "app.api.oauth.linkedin.exchange_code",
        side_effect=LinkedInOAuthError("invalid_code"),
    ):
        resp = await client.get(
            "/api/oauth/linkedin/callback?code=bad&state=s", follow_redirects=False
        )

    assert resp.status_code == 502


async def test_callback_consumes_state_before_processing(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace(owner_user_id=user.id)
    mock_redis.get = AsyncMock(return_value=str(user.id))

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    ws_result = MagicMock()
    ws_result.scalar_one_or_none.return_value = workspace
    mock_db.execute = AsyncMock(side_effect=[user_result, ws_result])

    with (
        patch("app.api.oauth.linkedin.exchange_code", return_value=_make_install_data()),
        patch("app.api.oauth.linkedin.upsert_tokens", new_callable=AsyncMock),
    ):
        await client.get(
            "/api/oauth/linkedin/callback?code=code&state=mystate", follow_redirects=False
        )

    mock_redis.delete.assert_called_once()
    deleted_key = mock_redis.delete.call_args[0][0]
    assert "mystate" in deleted_key


async def test_callback_redirects_to_seed_style_library(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace(owner_user_id=user.id)
    mock_redis.get = AsyncMock(return_value=str(user.id))

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    ws_result = MagicMock()
    ws_result.scalar_one_or_none.return_value = workspace
    mock_db.execute = AsyncMock(side_effect=[user_result, ws_result])

    with (
        patch("app.api.oauth.linkedin.exchange_code", return_value=_make_install_data()),
        patch("app.api.oauth.linkedin.upsert_tokens", new_callable=AsyncMock),
    ):
        resp = await client.get(
            "/api/oauth/linkedin/callback?code=code&state=s", follow_redirects=False
        )

    assert resp.status_code == 302
    assert "seed_style_library" in resp.headers["location"]


# ── upsert_tokens (service) ───────────────────────────────────────────────────


async def test_upsert_tokens_creates_two_rows():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    # Called twice: once for access token lookup, once for refresh token lookup
    db.execute = AsyncMock(return_value=none_result)

    workspace = _make_workspace()
    data = _make_install_data()

    await upsert_tokens(db, workspace, workspace.owner_user_id, data)

    # 2 OAuthToken rows + 1 AuditLog row
    assert db.add.call_count == 3
    added_types = [type(c[0][0]).__name__ for c in db.add.call_args_list]
    assert added_types.count("OAuthToken") == 2
    assert added_types.count("AuditLog") == 1


async def test_upsert_tokens_updates_existing_rows():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    workspace = _make_workspace()

    existing_access = OAuthToken(
        id=uuid4(),
        workspace_id=workspace.id,
        provider="linkedin_company",
        token_type="access",
        encrypted_token=b"old-access",
        nonce=b"\x00" * 12,
        tag=b"\x00" * 16,
        scopes="old:scope",
    )
    existing_refresh = OAuthToken(
        id=uuid4(),
        workspace_id=workspace.id,
        provider="linkedin_company",
        token_type="refresh",
        encrypted_token=b"old-refresh",
        nonce=b"\x00" * 12,
        tag=b"\x00" * 16,
        scopes="old:scope",
    )

    results = [
        MagicMock(**{"scalar_one_or_none.return_value": existing_access}),
        MagicMock(**{"scalar_one_or_none.return_value": existing_refresh}),
    ]
    db.execute = AsyncMock(side_effect=results)

    data = _make_install_data()
    await upsert_tokens(db, workspace, workspace.owner_user_id, data)

    # Only the AuditLog is added — tokens were updated in place
    assert db.add.call_count == 1
    assert type(db.add.call_args[0][0]).__name__ == "AuditLog"

    # Tokens were mutated
    assert existing_access.encrypted_token != b"old-access"
    assert existing_refresh.encrypted_token != b"old-refresh"
    assert existing_access.scopes == data.scopes
    assert existing_access.expires_at == data.access_token_expires_at
    assert existing_refresh.expires_at == data.refresh_token_expires_at


async def test_upsert_tokens_advances_onboarding_step():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=none_result)

    workspace = _make_workspace(onboarding_step="connect_linkedin")
    data = _make_install_data()

    await upsert_tokens(db, workspace, workspace.owner_user_id, data)

    assert workspace.onboarding_step == "seed_style_library"


async def test_upsert_tokens_does_not_regress_onboarding_step():
    """If onboarding is already past connect_linkedin, don't reset it."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=none_result)

    workspace = _make_workspace(onboarding_step="seed_style_library")
    data = _make_install_data()

    await upsert_tokens(db, workspace, workspace.owner_user_id, data)

    assert workspace.onboarding_step == "seed_style_library"


# ── exchange_code (service) ───────────────────────────────────────────────────


async def test_exchange_code_returns_install_data():
    from app.services.linkedin_oauth import exchange_code

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "access_token": "li-access-abc",
        "expires_in": 5183944,
        "refresh_token": "li-refresh-abc",
        "refresh_token_expires_in": 31536000,
        "scope": "openid profile email w_organization_social",
    }

    with patch("app.services.linkedin_oauth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await exchange_code("valid-code")

    assert result.access_token == "li-access-abc"
    assert result.refresh_token == "li-refresh-abc"
    assert result.scopes == "openid profile email w_organization_social"
    assert result.access_token_expires_at > datetime.now(tz=timezone.utc)
    assert result.refresh_token_expires_at > result.access_token_expires_at


async def test_exchange_code_raises_on_missing_access_token():
    from app.services.linkedin_oauth import exchange_code

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"error": "invalid_grant", "error_description": "bad code"}

    with patch("app.services.linkedin_oauth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(LinkedInOAuthError, match="invalid_grant"):
            await exchange_code("bad-code")


# ── refresh_token_for_workspace (service) ────────────────────────────────────


def _make_refresh_token_row(workspace_id=None) -> OAuthToken:
    """Return an OAuthToken row with a real encrypted refresh token."""
    from app.crypto import encrypt

    encrypted = encrypt("li-refresh-real-token")
    return OAuthToken(
        id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        provider="linkedin_company",
        token_type="refresh",
        encrypted_token=encrypted.ciphertext,
        nonce=encrypted.nonce,
        tag=encrypted.tag,
        scopes="openid profile email w_organization_social",
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=5),
    )


async def test_refresh_token_returns_true_and_updates_rows():
    from app.services.linkedin_oauth import refresh_token_for_workspace

    db = AsyncMock()
    db.flush = AsyncMock()

    workspace_id = uuid4()
    refresh_row = _make_refresh_token_row(workspace_id=workspace_id)

    existing_access = OAuthToken(
        id=uuid4(),
        workspace_id=workspace_id,
        provider="linkedin_company",
        token_type="access",
        encrypted_token=b"old-access",
        nonce=b"\x00" * 12,
        tag=b"\x00" * 16,
        scopes="old",
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=3),
    )

    access_result = MagicMock()
    access_result.scalar_one_or_none.return_value = existing_access
    db.execute = AsyncMock(return_value=access_result)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "access_token": "li-new-access",
        "expires_in": 5183944,
        "refresh_token": "li-new-refresh",
        "refresh_token_expires_in": 31536000,
    }

    with patch("app.services.linkedin_oauth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await refresh_token_for_workspace(db, refresh_row)

    assert result is True
    assert existing_access.encrypted_token != b"old-access"
    assert refresh_row.encrypted_token is not None
    db.flush.assert_called_once()


async def test_refresh_token_returns_false_on_http_error():
    from app.services.linkedin_oauth import refresh_token_for_workspace

    db = AsyncMock()
    refresh_row = _make_refresh_token_row()

    import httpx

    with patch("app.services.linkedin_oauth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        ))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await refresh_token_for_workspace(db, refresh_row)

    assert result is False


async def test_refresh_token_returns_false_when_response_missing_access_token():
    from app.services.linkedin_oauth import refresh_token_for_workspace

    db = AsyncMock()
    refresh_row = _make_refresh_token_row()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"error": "invalid_grant"}

    with patch("app.services.linkedin_oauth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await refresh_token_for_workspace(db, refresh_row)

    assert result is False


async def test_refresh_token_returns_false_on_decryption_failure():
    from app.services.linkedin_oauth import refresh_token_for_workspace

    db = AsyncMock()

    # Garbage bytes — decryption will fail authentication
    bad_row = OAuthToken(
        id=uuid4(),
        workspace_id=uuid4(),
        provider="linkedin_company",
        token_type="refresh",
        encrypted_token=b"garbage-ct",
        nonce=b"\x00" * 12,
        tag=b"\xff" * 16,  # wrong tag
        scopes="",
    )

    result = await refresh_token_for_workspace(db, bad_row)

    assert result is False


async def test_exchange_code_uses_fallback_expiry_when_omitted():
    from app.services.linkedin_oauth import (
        _DEFAULT_ACCESS_EXPIRES_SECONDS,
        _DEFAULT_REFRESH_EXPIRES_SECONDS,
        exchange_code,
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    # LinkedIn sometimes omits expiry fields for certain app types
    mock_response.json.return_value = {
        "access_token": "li-access-no-expiry",
        "refresh_token": "li-refresh-no-expiry",
    }

    with patch("app.services.linkedin_oauth.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await exchange_code("code-no-expiry")

    now = datetime.now(tz=timezone.utc)
    expected_access = now + timedelta(seconds=_DEFAULT_ACCESS_EXPIRES_SECONDS)
    expected_refresh = now + timedelta(seconds=_DEFAULT_REFRESH_EXPIRES_SECONDS)

    # Allow a few seconds of test execution time
    assert abs((result.access_token_expires_at - expected_access).total_seconds()) < 5
    assert abs((result.refresh_token_expires_at - expected_refresh).total_seconds()) < 5
