"""Tests for signals and drafts REST API endpoints.

GET  /api/signals
GET  /api/signals/{id}
POST /api/signals/{id}/approve
POST /api/signals/{id}/reject
POST /api/signals/{id}/rewrite
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/vesper_test")

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.content_signal import ContentSignal
from app.models.draft_post import DraftPost
from app.models.user import User
from app.models.workspace import Workspace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(**kwargs) -> User:
    return User(
        id=kwargs.get("id", uuid4()),
        email=kwargs.get("email", "user@example.com"),
        google_id="google-sub-123",
        display_name="Test User",
        avatar_url=None,
    )


def _make_workspace(**kwargs) -> Workspace:
    return Workspace(
        id=kwargs.get("id", uuid4()),
        name="Acme Corp",
        owner_user_id=uuid4(),
        slack_team_id="T123456",
        onboarding_step="done",
        onboarding_complete=True,
        settings={},
    )


def _make_signal(workspace_id, **kwargs) -> MagicMock:
    s = MagicMock(spec=ContentSignal)
    s.id = kwargs.get("id", uuid4())
    s.workspace_id = workspace_id
    s.signal_type = kwargs.get("signal_type", "product_win")
    s.summary = kwargs.get("summary", "Great win with Acme")
    s.status = kwargs.get("status", "in_review")
    s.source_type = "slack"
    s.source_channel = "C001"
    s.created_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    s.draft_posts = kwargs.get("draft_posts", [])
    s.metadata_ = kwargs.get("metadata_", {})
    return s


def _make_draft(signal_id, variant_number=1, **kwargs) -> MagicMock:
    dp = MagicMock(spec=DraftPost)
    dp.id = kwargs.get("id", uuid4())
    dp.content_signal_id = signal_id
    dp.variant_number = variant_number
    dp.body = kwargs.get("body", "A great post variant")
    dp.is_selected = kwargs.get("is_selected", False)
    dp.feedback = None
    dp.scheduled_at = None
    dp.published_at = None
    dp.created_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    dp.slack_message_ts = "1234567890.000001"
    dp.slack_channel_id = "C001"
    return dp


def _seed_session(
    mock_redis: AsyncMock,
    mock_db: AsyncMock,
    user: User,
    workspace: Workspace | None = None,
    extra_db_results: list | None = None,
) -> str:
    """Seed session cookie + mock_db to return user then workspace."""
    session_id = "test-session-id"
    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    workspace_result = MagicMock()
    workspace_result.scalar_one_or_none.return_value = workspace

    side_effects = [user_result, workspace_result] + (extra_db_results or [])
    mock_db.execute = AsyncMock(side_effect=side_effects)

    return session_id


_COOKIES = {"vesper_session": "test-session-id"}
_SCHEDULED_AT = "2026-05-01T09:00:00+00:00"


# ---------------------------------------------------------------------------
# GET /api/signals
# ---------------------------------------------------------------------------


async def test_list_signals_empty(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    _seed_session(mock_redis, mock_db, user, workspace)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            count_result,
            rows_result,
        ]
    )
    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))

    resp = await client.get("/api/signals", cookies=_COOKIES)

    assert resp.status_code == 200
    data = resp.json()
    assert data["signals"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["limit"] == 20


async def test_list_signals_returns_scoped_results(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal = _make_signal(workspace.id)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [signal]

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            count_result,
            rows_result,
        ]
    )

    resp = await client.get("/api/signals", cookies=_COOKIES)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["signals"]) == 1
    assert data["signals"][0]["summary"] == "Great win with Acme"
    assert data["signals"][0]["status"] == "in_review"
    assert data["total"] == 1


async def test_list_signals_pagination(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 25
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [_make_signal(workspace.id) for _ in range(5)]

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            count_result,
            rows_result,
        ]
    )

    resp = await client.get("/api/signals?page=2&limit=10", cookies=_COOKIES)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert data["page"] == 2
    assert data["limit"] == 10
    assert len(data["signals"]) == 5


async def test_list_signals_status_filter(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [
        _make_signal(workspace.id, status="scheduled"),
        _make_signal(workspace.id, status="scheduled"),
    ]

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            count_result,
            rows_result,
        ]
    )

    resp = await client.get("/api/signals?status=scheduled", cookies=_COOKIES)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(s["status"] == "scheduled" for s in data["signals"])


async def test_list_signals_requires_auth(client):
    resp = await client.get("/api/signals")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/signals/{id}
# ---------------------------------------------------------------------------


async def test_signal_detail_ok(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    draft1 = _make_draft(signal_id, variant_number=1)
    draft2 = _make_draft(signal_id, variant_number=2)
    signal = _make_signal(workspace.id, id=signal_id, draft_posts=[draft1, draft2])

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    resp = await client.get(f"/api/signals/{signal_id}", cookies=_COOKIES)

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(signal_id)
    assert len(data["draft_posts"]) == 2
    assert data["draft_posts"][0]["variant_number"] == 1


async def test_signal_detail_not_found(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
    )

    resp = await client.get(f"/api/signals/{uuid4()}", cookies=_COOKIES)

    assert resp.status_code == 404


async def test_signal_detail_wrong_workspace_returns_403(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    # Signal belongs to a different workspace
    signal = _make_signal(uuid4())

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    resp = await client.get(f"/api/signals/{signal.id}", cookies=_COOKIES)

    assert resp.status_code == 403


async def test_signal_detail_requires_auth(client):
    resp = await client.get(f"/api/signals/{uuid4()}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/signals/{id}/approve
# ---------------------------------------------------------------------------


async def test_approve_ok(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(workspace.id, id=signal_id)

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    with patch("app.api.drafts.approval.handle_approve", new_callable=AsyncMock) as mock_approve:
        resp = await client.post(
            f"/api/signals/{signal_id}/approve",
            json={"variant_number": 1, "scheduled_at": _SCHEDULED_AT},
            cookies=_COOKIES,
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_approve.assert_awaited_once()
    call_kwargs = mock_approve.call_args.kwargs
    assert call_kwargs["signal_id"] == signal_id
    assert call_kwargs["variant_number"] == 1
    assert call_kwargs["actor"] == user.email
    assert call_kwargs["body_override"] is None


async def test_approve_with_body_override(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(workspace.id, id=signal_id)

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    with patch("app.api.drafts.approval.handle_approve", new_callable=AsyncMock) as mock_approve:
        resp = await client.post(
            f"/api/signals/{signal_id}/approve",
            json={
                "variant_number": 1,
                "scheduled_at": _SCHEDULED_AT,
                "body_override": "Edited post text",
            },
            cookies=_COOKIES,
        )

    assert resp.status_code == 200
    call_kwargs = mock_approve.call_args.kwargs
    assert call_kwargs["body_override"] == "Edited post text"


async def test_approve_non_in_review_signal_returns_409(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(workspace.id, id=signal_id, status="scheduled")

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    resp = await client.post(
        f"/api/signals/{signal_id}/approve",
        json={"variant_number": 1, "scheduled_at": _SCHEDULED_AT},
        cookies=_COOKIES,
    )

    assert resp.status_code == 409


async def test_approve_naive_datetime_returns_422(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
        ]
    )

    resp = await client.post(
        f"/api/signals/{signal_id}/approve",
        # No timezone offset — bare ISO string
        json={"variant_number": 1, "scheduled_at": "2026-05-01T09:00:00"},
        cookies=_COOKIES,
    )

    assert resp.status_code == 422


async def test_approve_wrong_workspace_returns_403(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(uuid4(), id=signal_id)  # different workspace

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    resp = await client.post(
        f"/api/signals/{signal_id}/approve",
        json={"variant_number": 1, "scheduled_at": _SCHEDULED_AT},
        cookies=_COOKIES,
    )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/signals/{id}/reject
# ---------------------------------------------------------------------------


async def test_reject_ok(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(workspace.id, id=signal_id, status="in_review")

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    with patch("app.api.drafts.approval.handle_reject", new_callable=AsyncMock) as mock_reject:
        resp = await client.post(f"/api/signals/{signal_id}/reject", cookies=_COOKIES)

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_reject.assert_awaited_once_with(
        signal_id=signal_id, actor=user.email, db=mock_db
    )


async def test_reject_non_in_review_returns_409(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    # Any non-in_review status should be rejected — covers both terminal and pre-review states
    signal = _make_signal(workspace.id, id=signal_id, status="scheduled")

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    resp = await client.post(f"/api/signals/{signal_id}/reject", cookies=_COOKIES)

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/signals/{id}/rewrite
# ---------------------------------------------------------------------------


async def test_rewrite_ok(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(workspace.id, id=signal_id)

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    with patch("app.api.drafts.approval.handle_rewrite", new_callable=AsyncMock) as mock_rewrite:
        resp = await client.post(
            f"/api/signals/{signal_id}/rewrite",
            json={"variant_number": 2, "feedback": "Make it shorter"},
            cookies=_COOKIES,
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    call_kwargs = mock_rewrite.call_args.kwargs
    assert call_kwargs["variant_number"] == 2
    assert call_kwargs["feedback"] == "Make it shorter"
    assert call_kwargs["actor"] == user.email


async def test_rewrite_requires_auth(client):
    resp = await client.post(
        f"/api/signals/{uuid4()}/rewrite",
        json={"variant_number": 1, "feedback": "better"},
    )
    assert resp.status_code == 401


async def test_rewrite_wrong_workspace_returns_403(client, mock_redis, mock_db):
    user = _make_user()
    workspace = _make_workspace()
    signal_id = uuid4()
    signal = _make_signal(uuid4(), id=signal_id)  # different workspace

    mock_redis.get = AsyncMock(return_value=json.dumps({"user_id": str(user.id)}))
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=workspace)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=signal)),
        ]
    )

    resp = await client.post(
        f"/api/signals/{signal_id}/rewrite",
        json={"variant_number": 1, "feedback": "shorter"},
        cookies=_COOKIES,
    )

    assert resp.status_code == 403
