"""Tests for the approval service (handle_approve, handle_reject, handle_rewrite).

All tests are async (pytest-asyncio). The DB session is mocked throughout —
approval.py's _load_signal is patched to return fake ORM objects, so we never
hit a real database.

Block builder functions (_approved_blocks, _rejected_blocks, etc.) are tested
independently as pure functions.
"""

from __future__ import annotations

import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/vesper_test")

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.approval import (
    _approved_blocks,
    _get_card_coords,
    _max_rewrites_blocks,
    _rejected_blocks,
    _rewrite_blocks,
    handle_approve,
    handle_reject,
    handle_rewrite,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WS_ID = uuid4()
_SIG_ID = uuid4()
_SCHEDULED_AT = datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc)


def _make_draft_post(
    variant_number: int = 1,
    body: str = "Draft body",
    is_selected: bool = False,
    slack_message_ts: str | None = "1234567890.000001",
    slack_channel_id: str | None = "C001",
    feedback: str | None = None,
    scheduled_at: datetime | None = None,
) -> MagicMock:
    dp = MagicMock()
    dp.variant_number = variant_number
    dp.body = body
    dp.is_selected = is_selected
    dp.slack_message_ts = slack_message_ts
    dp.slack_channel_id = slack_channel_id
    dp.feedback = feedback
    dp.scheduled_at = scheduled_at
    return dp


def _make_signal(
    *,
    status: str = "in_review",
    summary: str = "We hit 1k users",
    metadata_: dict | None = None,
    draft_posts: list | None = None,
) -> MagicMock:
    signal = MagicMock()
    signal.id = _SIG_ID
    signal.workspace_id = _WS_ID
    signal.status = status
    signal.summary = summary
    signal.metadata_ = metadata_ if metadata_ is not None else {}
    signal.draft_posts = draft_posts if draft_posts is not None else [
        _make_draft_post(variant_number=1),
        _make_draft_post(variant_number=2, slack_message_ts=None, slack_channel_id=None),
    ]
    return signal


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Block builder tests (pure functions — no mocking needed)
# ---------------------------------------------------------------------------

def test_approved_blocks_has_no_action_buttons():
    blocks = _approved_blocks("Test signal", _SCHEDULED_AT, "alice")
    types = {b["type"] for b in blocks}
    assert "actions" not in types


def test_approved_blocks_contains_scheduled_text():
    blocks = _approved_blocks("Test signal", _SCHEDULED_AT, "alice")
    combined = " ".join(
        b.get("text", {}).get("text", "") for b in blocks if b["type"] == "section"
    )
    assert "alice" in combined
    assert "2026-05-01" in combined


def test_rejected_blocks_has_no_action_buttons():
    blocks = _rejected_blocks("Test signal", "bob")
    types = {b["type"] for b in blocks}
    assert "actions" not in types


def test_rejected_blocks_contains_actor():
    blocks = _rejected_blocks("Test signal", "bob")
    combined = " ".join(
        b.get("text", {}).get("text", "") for b in blocks if b["type"] == "section"
    )
    assert "bob" in combined


def test_rewrite_blocks_includes_count():
    blocks = _rewrite_blocks("Test signal", 2, "carol")
    combined = " ".join(
        b.get("text", {}).get("text", "") for b in blocks if b["type"] == "section"
    )
    assert "2/3" in combined
    assert "carol" in combined


def test_max_rewrites_blocks_has_no_action_buttons():
    blocks = _max_rewrites_blocks("Test signal", "dave")
    types = {b["type"] for b in blocks}
    assert "actions" not in types


def test_max_rewrites_blocks_contains_actor():
    blocks = _max_rewrites_blocks("Test signal", "dave")
    combined = " ".join(
        b.get("text", {}).get("text", "") for b in blocks if b["type"] == "section"
    )
    assert "dave" in combined


# ---------------------------------------------------------------------------
# _get_card_coords
# ---------------------------------------------------------------------------

def test_get_card_coords_returns_first_with_ts():
    dp1 = _make_draft_post(variant_number=1, slack_message_ts=None, slack_channel_id=None)
    dp2 = _make_draft_post(variant_number=2, slack_message_ts="ts.001", slack_channel_id="C999")
    result = _get_card_coords([dp1, dp2])
    assert result == ("ts.001", "C999")


def test_get_card_coords_returns_none_when_none_set():
    dp1 = _make_draft_post(slack_message_ts=None, slack_channel_id=None)
    assert _get_card_coords([dp1]) is None


def test_get_card_coords_empty_list():
    assert _get_card_coords([]) is None


# ---------------------------------------------------------------------------
# handle_approve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_sets_selected_and_scheduled():
    dp1 = _make_draft_post(variant_number=1)
    dp2 = _make_draft_post(variant_number=2, slack_message_ts=None, slack_channel_id=None)
    signal = _make_signal(draft_posts=[dp1, dp2])
    db = _make_db()

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=AsyncMock()),
    ):
        await handle_approve(_SIG_ID, 1, _SCHEDULED_AT, "alice", db)

    assert dp1.is_selected is True
    assert dp1.scheduled_at == _SCHEDULED_AT
    assert dp2.is_selected is False
    assert signal.status == "scheduled"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_signal_not_found_does_nothing():
    db = _make_db()
    with patch("app.services.approval._load_signal", new=AsyncMock(return_value=None)):
        await handle_approve(_SIG_ID, 1, _SCHEDULED_AT, "alice", db)

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_updates_slack_card():
    signal = _make_signal()
    db = _make_db()
    mock_to_thread = AsyncMock()

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=mock_to_thread),
    ):
        await handle_approve(_SIG_ID, 1, _SCHEDULED_AT, "alice", db)

    mock_to_thread.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_slack_failure_is_nonfatal():
    from app.services.slack_client import SlackClientError

    signal = _make_signal()
    db = _make_db()

    async def _raise(*_a, **_kw):
        raise SlackClientError("boom")

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=_raise),
    ):
        # Should not raise
        await handle_approve(_SIG_ID, 1, _SCHEDULED_AT, "alice", db)


@pytest.mark.asyncio
async def test_approve_no_slack_update_when_no_card_coords():
    dp1 = _make_draft_post(slack_message_ts=None, slack_channel_id=None)
    signal = _make_signal(draft_posts=[dp1])
    db = _make_db()
    mock_to_thread = AsyncMock()

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=mock_to_thread),
    ):
        await handle_approve(_SIG_ID, 1, _SCHEDULED_AT, "alice", db)

    mock_to_thread.assert_not_awaited()


# ---------------------------------------------------------------------------
# handle_reject
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_sets_status_failed():
    signal = _make_signal()
    db = _make_db()

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=AsyncMock()),
    ):
        await handle_reject(_SIG_ID, "bob", db)

    assert signal.status == "failed"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_signal_not_found_does_nothing():
    db = _make_db()
    with patch("app.services.approval._load_signal", new=AsyncMock(return_value=None)):
        await handle_reject(_SIG_ID, "bob", db)

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reject_updates_slack_card():
    signal = _make_signal()
    db = _make_db()
    mock_to_thread = AsyncMock()

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=mock_to_thread),
    ):
        await handle_reject(_SIG_ID, "bob", db)

    mock_to_thread.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_rewrite
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rewrite_stores_feedback_on_target_variant():
    dp1 = _make_draft_post(variant_number=1)
    dp2 = _make_draft_post(variant_number=2, slack_message_ts=None, slack_channel_id=None)
    signal = _make_signal(draft_posts=[dp1, dp2])
    db = _make_db()

    import app.workers.draft_pipeline as dp_mod
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    orig = dp_mod.rewrite_draft
    dp_mod.rewrite_draft = mock_task

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=AsyncMock()),
    ):
        try:
            await handle_rewrite(_SIG_ID, 1, "make it shorter", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    assert dp1.feedback == "make it shorter"
    assert dp2.feedback != "make it shorter"  # other variant untouched


@pytest.mark.asyncio
async def test_rewrite_increments_count():
    signal = _make_signal(metadata_={"rewrite_count": 1})
    db = _make_db()

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=AsyncMock()),
    ):
        import app.workers.draft_pipeline as dp_mod
        mock_task = MagicMock()
        mock_task.delay = MagicMock()
        orig = dp_mod.rewrite_draft
        dp_mod.rewrite_draft = mock_task
        try:
            await handle_rewrite(_SIG_ID, 1, "be more specific", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    assert signal.metadata_["rewrite_count"] == 2
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_dispatches_rewrite_draft_task():
    signal = _make_signal()
    db = _make_db()

    import app.workers.draft_pipeline as dp_mod
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    orig = dp_mod.rewrite_draft
    dp_mod.rewrite_draft = mock_task

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=AsyncMock()),
    ):
        try:
            await handle_rewrite(_SIG_ID, 1, "shorter please", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    mock_task.delay.assert_called_once_with(str(_SIG_ID), 1)


@pytest.mark.asyncio
async def test_rewrite_updates_slack_card():
    signal = _make_signal()
    db = _make_db()
    mock_to_thread = AsyncMock()

    import app.workers.draft_pipeline as dp_mod
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    orig = dp_mod.rewrite_draft
    dp_mod.rewrite_draft = mock_task

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=mock_to_thread),
    ):
        try:
            await handle_rewrite(_SIG_ID, 1, "longer please", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    mock_to_thread.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_at_cap_does_not_dispatch():
    # rewrite_count already 3 — next increment hits 4 > 3 cap
    signal = _make_signal(metadata_={"rewrite_count": 3})
    db = _make_db()

    import app.workers.draft_pipeline as dp_mod
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    orig = dp_mod.rewrite_draft
    dp_mod.rewrite_draft = mock_task

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=AsyncMock()),
    ):
        try:
            await handle_rewrite(_SIG_ID, 1, "one more try", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    mock_task.delay.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_rewrite_at_cap_shows_max_rewrites_card():
    signal = _make_signal(metadata_={"rewrite_count": 3})
    db = _make_db()
    mock_to_thread = AsyncMock()

    import app.workers.draft_pipeline as dp_mod
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    orig = dp_mod.rewrite_draft
    dp_mod.rewrite_draft = mock_task

    captured_blocks: list = []

    async def _capture(fn):
        captured_blocks.extend(fn())

    with (
        patch("app.services.approval._load_signal", new=AsyncMock(return_value=signal)),
        patch("app.services.approval.asyncio.to_thread", new=mock_to_thread),
    ):
        try:
            await handle_rewrite(_SIG_ID, 1, "one more try", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    # Card update should still be called (to show max-rewrites message)
    mock_to_thread.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_signal_not_found_does_nothing():
    db = _make_db()
    import app.workers.draft_pipeline as dp_mod
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    orig = dp_mod.rewrite_draft
    dp_mod.rewrite_draft = mock_task

    with patch("app.services.approval._load_signal", new=AsyncMock(return_value=None)):
        try:
            await handle_rewrite(_SIG_ID, 1, "feedback", "carol", db)
        finally:
            dp_mod.rewrite_draft = orig

    mock_task.delay.assert_not_called()
    db.commit.assert_not_awaited()
