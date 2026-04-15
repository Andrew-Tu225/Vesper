"""Tests for onboarding API routes (GET + POST /api/onboarding/channels)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.models.workspace import Workspace
from app.services.slack_client import SlackClientError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(**kwargs) -> User:
    return User(
        id=kwargs.get("id", uuid4()),
        email=kwargs.get("email", "user@example.com"),
        google_id=kwargs.get("google_id", "google-sub-123"),
        display_name=kwargs.get("display_name", "Test User"),
        avatar_url=None,
    )


def _make_workspace(**kwargs) -> Workspace:
    return Workspace(
        id=kwargs.get("id", uuid4()),
        name=kwargs.get("name", "Acme Corp"),
        owner_user_id=kwargs.get("owner_user_id", uuid4()),
        slack_team_id=kwargs.get("slack_team_id", "T123456"),
        onboarding_step=kwargs.get("onboarding_step", "channels_setup"),
        onboarding_complete=kwargs.get("onboarding_complete", False),
        settings=kwargs.get("settings", {}),
    )


def _seed_session(mock_redis: AsyncMock, mock_db: AsyncMock, user: User, workspace: Workspace | None = None) -> str:
    """Seed session cookie + mock_db to return user (and optionally workspace)."""
    session_id = "test-session-id"
    session_data = json.dumps({"user_id": str(user.id)})
    mock_redis.get = AsyncMock(return_value=session_data)

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    workspace_result = MagicMock()
    workspace_result.scalar_one_or_none.return_value = workspace

    # First execute call = user lookup; second = workspace lookup
    mock_db.execute = AsyncMock(side_effect=[user_result, workspace_result])

    return session_id


_RAW_CHANNELS = [
    {"id": "C001", "name": "general", "num_members": 10},
    {"id": "C002", "name": "engineering", "num_members": 5},
]


# ---------------------------------------------------------------------------
# GET /api/onboarding/channels
# ---------------------------------------------------------------------------


async def test_get_channels_returns_list(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    _seed_session(mock_redis, mock_db, user, workspace)

    mock_client = MagicMock()
    with (
        patch("app.api.onboarding.get_workspace_client", return_value=mock_client),
        patch("app.api.onboarding.list_channels", return_value=_RAW_CHANNELS),
    ):
        resp = await client.get(
            "/api/onboarding/channels",
            cookies={"vesper_session": "test-session-id"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["channels"]) == 2
    assert data["channels"][0]["id"] == "C001"
    assert data["channels"][0]["name"] == "general"
    assert data["channels"][0]["member_count"] == 10


async def test_get_channels_requires_auth(client):
    resp = await client.get("/api/onboarding/channels")

    assert resp.status_code == 401


async def test_get_channels_no_workspace_returns_400(client, mock_redis, mock_db):
    user = _make_user()
    _seed_session(mock_redis, mock_db, user, workspace=None)

    resp = await client.get(
        "/api/onboarding/channels",
        cookies={"vesper_session": "test-session-id"},
    )

    assert resp.status_code == 400
    assert "workspace" in resp.json()["detail"].lower()


async def test_get_channels_slack_error_returns_503(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    _seed_session(mock_redis, mock_db, user, workspace)

    with patch(
        "app.api.onboarding.get_workspace_client",
        side_effect=SlackClientError("No bot token"),
    ):
        resp = await client.get(
            "/api/onboarding/channels",
            cookies={"vesper_session": "test-session-id"},
        )

    assert resp.status_code == 503
    assert "Slack" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/onboarding/channels
# ---------------------------------------------------------------------------


async def test_post_channels_saves_and_completes_onboarding(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    _seed_session(mock_redis, mock_db, user, workspace)

    resp = await client.post(
        "/api/onboarding/channels",
        json={"channel_ids": ["C001", "C002"]},
        cookies={"vesper_session": "test-session-id"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enrichment_channels"] == ["C001", "C002"]

    # Workspace mutations applied
    assert workspace.onboarding_complete is True
    assert workspace.onboarding_step == "done"
    assert workspace.settings["enrichment_channels"] == ["C001", "C002"]

    # DB committed
    mock_db.commit.assert_awaited_once()


async def test_post_channels_empty_list_returns_422(client, mock_redis, mock_db):
    user = _make_user()
    _seed_session(mock_redis, mock_db, user, workspace=_make_workspace())

    resp = await client.post(
        "/api/onboarding/channels",
        json={"channel_ids": []},
        cookies={"vesper_session": "test-session-id"},
    )

    assert resp.status_code == 422


async def test_post_channels_requires_auth(client):
    resp = await client.post(
        "/api/onboarding/channels",
        json={"channel_ids": ["C001"]},
    )

    assert resp.status_code == 401


async def test_post_channels_writes_audit_log(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    _seed_session(mock_redis, mock_db, user, workspace)

    await client.post(
        "/api/onboarding/channels",
        json={"channel_ids": ["C001"]},
        cookies={"vesper_session": "test-session-id"},
    )

    # db.add should be called once for the AuditLog
    mock_db.add.assert_called_once()
    audit_arg = mock_db.add.call_args[0][0]
    assert audit_arg.action == "channels_setup"
    assert audit_arg.entity_type == "workspace"
    assert audit_arg.actor == user.email
    assert audit_arg.new_value == {"enrichment_channels": ["C001"]}


async def test_post_channels_deduplicates_ids(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    _seed_session(mock_redis, mock_db, user, workspace)

    resp = await client.post(
        "/api/onboarding/channels",
        json={"channel_ids": ["C001", "C002", "C001"]},
        cookies={"vesper_session": "test-session-id"},
    )

    assert resp.status_code == 200
    assert resp.json()["enrichment_channels"] == ["C001", "C002"]
