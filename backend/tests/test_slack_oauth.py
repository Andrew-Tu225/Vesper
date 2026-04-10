"""Tests for Slack OAuth routes and service functions."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.models.workspace import Workspace
from app.services.slack_oauth import (
    SlackInstallData,
    SlackOAuthError,
    build_install_url,
    upsert_workspace_and_token,
)


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
        onboarding_step=kwargs.get("onboarding_step", "connect_slack"),
    )


def _make_install_data(**kwargs) -> SlackInstallData:
    return SlackInstallData(
        team_id=kwargs.get("team_id", "T123456"),
        team_name=kwargs.get("team_name", "Acme Corp"),
        bot_token=kwargs.get("bot_token", "xoxb-test-token"),
        bot_scopes=kwargs.get("bot_scopes", "channels:history,channels:read"),
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


# ── GET /api/oauth/slack/install ──────────────────────────────────────────────


async def test_install_requires_auth(client):
    resp = await client.get("/api/oauth/slack/install", follow_redirects=False)

    assert resp.status_code == 401


async def test_install_redirects_to_slack(client, mock_redis, mock_db):
    user = _make_user()
    session_id = _seed_session(mock_redis, mock_db, user)

    resp = await client.get(
        "/api/oauth/slack/install",
        cookies={"vesper_session": session_id},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "slack.com/oauth/v2/authorize" in location
    assert "scope=" in location
    assert "state=" in location


async def test_install_stores_user_id_in_redis(client, mock_redis, mock_db):
    user = _make_user()
    session_id = _seed_session(mock_redis, mock_db, user)

    await client.get(
        "/api/oauth/slack/install",
        cookies={"vesper_session": session_id},
        follow_redirects=False,
    )

    set_calls = [c for c in mock_redis.set.call_args_list if "slack_oauth_state:" in c[0][0]]
    assert len(set_calls) == 1
    key, value = set_calls[0][0]
    assert key.startswith("slack_oauth_state:")
    assert value == str(user.id)
    assert set_calls[0][1]["ex"] == 600


# ── GET /api/oauth/slack/callback ─────────────────────────────────────────────


async def test_callback_missing_state_returns_400(client, mock_redis):
    mock_redis.get = AsyncMock(return_value=None)

    resp = await client.get(
        "/api/oauth/slack/callback?code=abc&state=stale", follow_redirects=False
    )

    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


async def test_callback_consumes_state_before_processing(client, mock_redis, mock_db):
    user = _make_user()
    user_id_str = str(user.id)
    mock_redis.get = AsyncMock(return_value=user_id_str)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    workspace = _make_workspace(owner_user_id=user.id)

    with (
        patch("app.api.oauth.slack.exchange_code", return_value=_make_install_data()),
        patch("app.api.oauth.slack.upsert_workspace_and_token", return_value=workspace),
    ):
        await client.get(
            "/api/oauth/slack/callback?code=code&state=mystate", follow_redirects=False
        )

    mock_redis.delete.assert_called_once()
    deleted_key = mock_redis.delete.call_args[0][0]
    assert "mystate" in deleted_key


async def test_callback_slack_api_error_returns_502(client, mock_redis, mock_db):
    user = _make_user()
    mock_redis.get = AsyncMock(return_value=str(user.id))

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.api.oauth.slack.exchange_code", side_effect=SlackOAuthError("invalid_code")
    ):
        resp = await client.get(
            "/api/oauth/slack/callback?code=bad&state=s", follow_redirects=False
        )

    assert resp.status_code == 502


async def test_callback_generic_exception_returns_502(client, mock_redis, mock_db):
    user = _make_user()
    mock_redis.get = AsyncMock(return_value=str(user.id))

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.oauth.slack.exchange_code", side_effect=Exception("network error")):
        resp = await client.get(
            "/api/oauth/slack/callback?code=bad&state=s", follow_redirects=False
        )

    assert resp.status_code == 502


async def test_callback_redirects_to_onboarding(client, mock_redis, mock_db):
    user = _make_user()
    mock_redis.get = AsyncMock(return_value=str(user.id))

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    workspace = _make_workspace(owner_user_id=user.id)

    with (
        patch("app.api.oauth.slack.exchange_code", return_value=_make_install_data()),
        patch("app.api.oauth.slack.upsert_workspace_and_token", return_value=workspace),
    ):
        resp = await client.get(
            "/api/oauth/slack/callback?code=code&state=s", follow_redirects=False
        )

    assert resp.status_code == 302
    assert "connect_linkedin" in resp.headers["location"]


async def test_callback_user_not_found_returns_401(client, mock_redis, mock_db):
    mock_redis.get = AsyncMock(return_value=str(uuid4()))

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    resp = await client.get(
        "/api/oauth/slack/callback?code=code&state=s", follow_redirects=False
    )

    assert resp.status_code == 401


# ── build_install_url (service) ───────────────────────────────────────────────


def test_build_install_url_contains_required_params():
    url = build_install_url("test-state-abc")

    assert "slack.com/oauth/v2/authorize" in url
    assert "scope=" in url
    assert "state=test-state-abc" in url
    assert "redirect_uri=" in url


def test_build_install_url_includes_client_id():
    from app.config import settings

    url = build_install_url("s")

    assert f"client_id={settings.slack_client_id}" in url


# ── upsert_workspace_and_token (service) ─────────────────────────────────────


async def test_upsert_creates_new_workspace_when_not_found():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=none_result)

    user = _make_user()
    data = _make_install_data(team_id="T_NEW", team_name="New Team", bot_token="xoxb-new")

    workspace = await upsert_workspace_and_token(db, user, data)

    assert db.add.call_count >= 1  # workspace + member + token
    assert workspace.slack_team_id == "T_NEW"
    assert workspace.name == "New Team"


async def test_upsert_advances_onboarding_step():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    existing_workspace = _make_workspace(onboarding_step="connect_slack")

    results = [
        MagicMock(**{"scalar_one_or_none.return_value": existing_workspace}),  # workspace
        MagicMock(**{"scalar_one_or_none.return_value": None}),                # member
        MagicMock(**{"scalar_one_or_none.return_value": None}),                # token
    ]
    db.execute = AsyncMock(side_effect=results)

    user = _make_user()
    data = _make_install_data(team_id=existing_workspace.slack_team_id)

    await upsert_workspace_and_token(db, user, data)

    assert existing_workspace.onboarding_step == "connect_linkedin"


async def test_upsert_updates_existing_token():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    from app.models.oauth_token import OAuthToken

    existing_workspace = _make_workspace(onboarding_step="connect_linkedin")
    existing_token = OAuthToken(
        id=uuid4(),
        workspace_id=existing_workspace.id,
        provider="slack",
        token_type="bot",
        encrypted_token=b"old",
        nonce=b"\x00" * 12,
        tag=b"\x00" * 16,
        scopes="old:scope",
    )

    from app.models.workspace_member import WorkspaceMember

    existing_member = WorkspaceMember(workspace_id=existing_workspace.id, user_id=uuid4())

    results = [
        MagicMock(**{"scalar_one_or_none.return_value": existing_workspace}),  # workspace
        MagicMock(**{"scalar_one_or_none.return_value": existing_member}),     # member (found)
        MagicMock(**{"scalar_one_or_none.return_value": existing_token}),      # token (found)
    ]
    db.execute = AsyncMock(side_effect=results)

    user = _make_user()
    data = _make_install_data(
        team_id=existing_workspace.slack_team_id,
        bot_token="xoxb-new-token",
        bot_scopes="channels:history,channels:read",
    )

    await upsert_workspace_and_token(db, user, data)

    # nothing new was added — workspace, member, and token all existed
    db.add.assert_not_called()
    assert existing_token.scopes == "channels:history,channels:read"
    # encrypted_token was replaced (not the old b"old" bytes)
    assert existing_token.encrypted_token != b"old"


# ── exchange_code (service) ───────────────────────────────────────────────────


async def test_exchange_code_returns_install_data():
    from app.services.slack_oauth import exchange_code

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "access_token": "xoxb-real-token",
        "scope": "channels:history,channels:read",
        "team": {"id": "T_REAL", "name": "Real Team"},
    }

    with patch("app.services.slack_oauth.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await exchange_code("valid-code")

    assert result.team_id == "T_REAL"
    assert result.team_name == "Real Team"
    assert result.bot_token == "xoxb-real-token"
    assert result.bot_scopes == "channels:history,channels:read"


async def test_exchange_code_raises_slack_oauth_error_on_ok_false():
    from app.services.slack_oauth import SlackOAuthError, exchange_code

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"ok": False, "error": "invalid_code"}

    with patch("app.services.slack_oauth.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(SlackOAuthError, match="invalid_code"):
            await exchange_code("bad-code")


async def test_upsert_does_not_duplicate_workspace():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    existing_workspace = _make_workspace(onboarding_step="connect_linkedin")

    results = [
        MagicMock(**{"scalar_one_or_none.return_value": existing_workspace}),  # workspace found
        MagicMock(**{"scalar_one_or_none.return_value": None}),                # member
        MagicMock(**{"scalar_one_or_none.return_value": None}),                # token
    ]
    db.execute = AsyncMock(side_effect=results)

    user = _make_user()
    data = _make_install_data(team_id=existing_workspace.slack_team_id)

    workspace = await upsert_workspace_and_token(db, user, data)

    # workspace.id must be the existing one, not a new object
    assert workspace.id == existing_workspace.id
