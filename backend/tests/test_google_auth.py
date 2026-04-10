"""Tests for Google OAuth routes, service functions, and the get_current_user dependency."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.google_auth import GoogleUserInfo, build_auth_url, upsert_user


def _make_user(**kwargs) -> User:
    user = User(
        id=kwargs.get("id", uuid4()),
        email=kwargs.get("email", "test@example.com"),
        google_id=kwargs.get("google_id", "google-sub-123"),
        display_name=kwargs.get("display_name", "Test User"),
        avatar_url=kwargs.get("avatar_url", None),
    )
    return user


def _make_google_user(**kwargs) -> GoogleUserInfo:
    return GoogleUserInfo(
        google_id=kwargs.get("google_id", "google-sub-123"),
        email=kwargs.get("email", "test@example.com"),
        display_name=kwargs.get("display_name", "Test User"),
        avatar_url=kwargs.get("avatar_url", None),
    )


# ── GET /api/auth/google/login ────────────────────────────────────────────────


async def test_login_redirects_to_google(client, mock_redis):
    resp = await client.get("/api/auth/google/login", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "accounts.google.com" in location
    assert "response_type=code" in location
    assert "scope=" in location
    assert "state=" in location


async def test_login_stores_state_in_redis(client, mock_redis):
    await client.get("/api/auth/google/login", follow_redirects=False)

    mock_redis.set.assert_called_once()
    key, value = mock_redis.set.call_args[0]
    assert key.startswith("google_oauth_state:")
    assert value == "1"
    assert mock_redis.set.call_args[1]["ex"] == 600


# ── GET /api/auth/google/callback ─────────────────────────────────────────────


async def test_callback_missing_state_returns_400(client, mock_redis):
    mock_redis.get = AsyncMock(return_value=None)

    resp = await client.get(
        "/api/auth/google/callback?code=abc&state=stale", follow_redirects=False
    )

    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


async def test_callback_deletes_state_after_use(client, mock_redis):
    mock_redis.get = AsyncMock(return_value="1")
    user = _make_user()

    with (
        patch("app.api.auth.google.exchange_code", return_value=_make_google_user()),
        patch("app.api.auth.google.upsert_user", return_value=user),
    ):
        await client.get(
            "/api/auth/google/callback?code=code&state=mystate", follow_redirects=False
        )

    mock_redis.delete.assert_called_once()
    deleted_key = mock_redis.delete.call_args[0][0]
    assert "mystate" in deleted_key


async def test_callback_google_error_returns_502(client, mock_redis):
    mock_redis.get = AsyncMock(return_value="1")

    with patch("app.api.auth.google.exchange_code", side_effect=Exception("token error")):
        resp = await client.get(
            "/api/auth/google/callback?code=bad&state=s", follow_redirects=False
        )

    assert resp.status_code == 502


async def test_callback_sets_session_cookie(client, mock_redis):
    mock_redis.get = AsyncMock(return_value="1")
    user = _make_user()

    with (
        patch("app.api.auth.google.exchange_code", return_value=_make_google_user()),
        patch("app.api.auth.google.upsert_user", return_value=user),
    ):
        resp = await client.get(
            "/api/auth/google/callback?code=code&state=s", follow_redirects=False
        )

    assert resp.status_code == 302
    assert "vesper_session" in resp.cookies


async def test_callback_stores_user_id_in_redis_session(client, mock_redis):
    mock_redis.get = AsyncMock(return_value="1")
    user = _make_user()

    with (
        patch("app.api.auth.google.exchange_code", return_value=_make_google_user()),
        patch("app.api.auth.google.upsert_user", return_value=user),
    ):
        await client.get(
            "/api/auth/google/callback?code=code&state=s", follow_redirects=False
        )

    # Second call to set is for the session (first was state deletion via delete, not set)
    session_calls = [
        c for c in mock_redis.set.call_args_list if c[0][0].startswith("session:")
    ]
    assert len(session_calls) == 1
    stored = json.loads(session_calls[0][0][1])
    assert stored["user_id"] == str(user.id)
    assert session_calls[0][1]["ex"] == 86400


async def test_callback_redirects_to_dashboard(client, mock_redis):
    mock_redis.get = AsyncMock(return_value="1")
    user = _make_user()

    with (
        patch("app.api.auth.google.exchange_code", return_value=_make_google_user()),
        patch("app.api.auth.google.upsert_user", return_value=user),
    ):
        resp = await client.get(
            "/api/auth/google/callback?code=code&state=s", follow_redirects=False
        )

    assert "/dashboard" in resp.headers["location"]


# ── POST /api/auth/google/logout ──────────────────────────────────────────────


async def test_logout_deletes_session_from_redis(client, mock_redis):
    resp = await client.post(
        "/api/auth/google/logout",
        cookies={"vesper_session": "my-session-id"},
    )

    assert resp.status_code == 200
    mock_redis.delete.assert_called_once_with("session:my-session-id")


async def test_logout_returns_ok(client, mock_redis):
    resp = await client.post(
        "/api/auth/google/logout",
        cookies={"vesper_session": "sess"},
    )

    assert resp.json() == {"ok": True}


async def test_logout_without_cookie_still_returns_200(client, mock_redis):
    resp = await client.post("/api/auth/google/logout")

    assert resp.status_code == 200
    mock_redis.delete.assert_not_called()


# ── GET /api/auth/google/me ───────────────────────────────────────────────────


async def test_me_without_cookie_returns_401(client):
    resp = await client.get("/api/auth/google/me")

    assert resp.status_code == 401


async def test_me_with_expired_session_returns_401(client, mock_redis):
    mock_redis.get = AsyncMock(return_value=None)

    resp = await client.get(
        "/api/auth/google/me", cookies={"vesper_session": "old-session"}
    )

    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


async def test_me_with_valid_session_returns_user(client, mock_redis, mock_db):
    user = _make_user()
    session_data = json.dumps({"user_id": str(user.id)})
    mock_redis.get = AsyncMock(return_value=session_data)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get(
        "/api/auth/google/me", cookies={"vesper_session": "valid-session"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == user.email
    assert body["id"] == str(user.id)
    assert body["display_name"] == user.display_name


# ── build_auth_url (service) ──────────────────────────────────────────────────


def test_build_auth_url_contains_required_params():
    url = build_auth_url("test-state-value")

    assert "accounts.google.com" in url
    assert "response_type=code" in url
    assert "scope=" in url
    assert "state=test-state-value" in url


def test_build_auth_url_includes_client_id():
    from app.config import settings

    url = build_auth_url("s")

    assert f"client_id={settings.google_client_id}" in url


# ── upsert_user (service) ─────────────────────────────────────────────────────


async def test_upsert_user_creates_new_user_when_not_found():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    # Both google_id and email lookups return nothing
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=none_result)

    info = GoogleUserInfo(
        google_id="new-gid",
        email="new@example.com",
        display_name="New User",
        avatar_url=None,
    )

    user = await upsert_user(db, info)

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert user.email == "new@example.com"
    assert user.google_id == "new-gid"


async def test_upsert_user_updates_existing_user_by_google_id():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    existing = _make_user(google_id="gid-123", display_name="Old Name")
    found_result = MagicMock()
    found_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=found_result)

    info = GoogleUserInfo(
        google_id="gid-123",
        email=existing.email,
        display_name="Updated Name",
        avatar_url="https://example.com/new.jpg",
    )

    user = await upsert_user(db, info)

    db.add.assert_not_called()
    assert user.display_name == "Updated Name"
    assert user.avatar_url == "https://example.com/new.jpg"


async def test_upsert_user_falls_back_to_email_lookup():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    existing = _make_user(google_id="old-gid", email="same@example.com")

    # First call (by google_id) returns None, second (by email) returns the user
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    found_result = MagicMock()
    found_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(side_effect=[none_result, found_result])

    info = GoogleUserInfo(
        google_id="new-gid",
        email="same@example.com",
        display_name="Same User",
        avatar_url=None,
    )

    user = await upsert_user(db, info)

    db.add.assert_not_called()
    # google_id re-linked to new value
    assert user.google_id == "new-gid"
