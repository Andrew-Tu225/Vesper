"""Tests for intake scanner tasks.

These are synchronous tests (plain def, not async) because the Celery tasks
call asyncio.run() internally and cannot be run inside an already-running loop.

Calling convention for bound Celery tasks:
  task.run(arg1, arg2)   — runs synchronously, injects the real task instance as self
  task.retry             — can be patched directly on the task object for retry testing
"""

from __future__ import annotations

import os

# Set required env vars before importing any worker module — Celery reads them
# at module load time.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/vesper_test")

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.workers.intake import scan_slack_channels
from app.workers.maintenance import dispatch_intake_scans


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WS_ID = str(uuid4())


def _make_ws_settings(channels=None, last_scanned=None):
    return {
        "enrichment_channels": channels if channels is not None else ["C001"],
        "last_slack_scanned_at": last_scanned,
        "social_queue_channel": "vesper-ai",
    }


def _make_classify_result(source_ids=None, embed_ids=None):
    from app.services.schemas import BatchClassifyResponse, ContentSignalCandidate

    candidate = ContentSignalCandidate(
        source_ids=source_ids or ["ts1"],
        signal_type="product_win",
        summary="Great product update",
        reason="High engagement",
    )
    return BatchClassifyResponse(
        candidates=[candidate],
        embed_message_ids=embed_ids or ["ts1"],
    )


# ---------------------------------------------------------------------------
# scan_slack_channels — early exits
# ---------------------------------------------------------------------------


def test_scan_skips_when_workspace_not_found():
    with patch("app.workers.intake._load_workspace_row", return_value=None):
        scan_slack_channels.run(_WS_ID)  # should not raise


def test_scan_skips_when_no_enrichment_channels():
    with patch(
        "app.workers.intake._load_workspace_row",
        return_value=_make_ws_settings(channels=[]),
    ):
        scan_slack_channels.run(_WS_ID)  # should not raise


def test_scan_updates_checkpoint_when_no_messages():
    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch("app.workers.intake._fetch_all_messages", return_value=([], {})),
        patch("app.workers.intake._update_last_scanned") as mock_update,
    ):
        scan_slack_channels.run(_WS_ID)

    mock_update.assert_called_once_with(_WS_ID)


# ---------------------------------------------------------------------------
# scan_slack_channels — error handling
# ---------------------------------------------------------------------------


def test_scan_retries_on_slack_client_error():
    from app.services.slack_client import SlackClientError

    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch(
            "app.services.slack_client.get_workspace_client",
            side_effect=SlackClientError("connection failed"),
        ),
        patch.object(scan_slack_channels, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            scan_slack_channels.run(_WS_ID)


def test_scan_retries_on_classifier_error():
    from app.services.classifier import ClassifierError

    msg = MagicMock()
    msg.source_id = "ts1"

    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch(
            "app.workers.intake._fetch_all_messages",
            return_value=([msg], {"ts1": {"_channel_id": "C001", "text": "hello"}}),
        ),
        patch(
            "app.workers.intake.asyncio.run",
            side_effect=ClassifierError("openai down"),
        ),
        patch.object(scan_slack_channels, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            scan_slack_channels.run(_WS_ID)


# ---------------------------------------------------------------------------
# scan_slack_channels — happy path
# ---------------------------------------------------------------------------


def test_scan_happy_path_creates_signal_and_dispatches():
    classify_result = _make_classify_result()
    signal_id = str(uuid4())

    mock_redis = MagicMock()
    mock_redis.set.return_value = True  # dedup not hit

    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch(
            "app.workers.intake._fetch_all_messages",
            return_value=(
                [MagicMock(source_id="ts1")],
                {"ts1": {"_channel_id": "C001", "text": "great news", "user": "U1"}},
            ),
        ),
        patch("app.workers.intake.asyncio.run", return_value=classify_result),
        patch("app.workers.intake._upsert_embeddings"),
        patch("app.redis_sync.get_sync_redis", return_value=mock_redis),
        patch("app.workers.intake._create_content_signal", return_value=signal_id),
        patch("app.workers.draft_pipeline.run_draft_pipeline") as mock_dispatch,
        patch("app.workers.intake._update_last_scanned") as mock_update,
    ):
        scan_slack_channels.run(_WS_ID)

    mock_dispatch.assert_called_once_with(signal_id)
    mock_update.assert_called_once_with(_WS_ID)


def test_scan_skips_signal_on_dedup_hit():
    classify_result = _make_classify_result()

    mock_redis = MagicMock()
    mock_redis.set.return_value = None  # dedup hit — key already exists

    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch(
            "app.workers.intake._fetch_all_messages",
            return_value=(
                [MagicMock(source_id="ts1")],
                {"ts1": {"_channel_id": "C001", "text": "great news", "user": "U1"}},
            ),
        ),
        patch("app.workers.intake.asyncio.run", return_value=classify_result),
        patch("app.workers.intake._upsert_embeddings"),
        patch("app.redis_sync.get_sync_redis", return_value=mock_redis),
        patch("app.workers.intake._create_content_signal") as mock_create,
        patch("app.workers.draft_pipeline.run_draft_pipeline") as mock_dispatch,
        patch("app.workers.intake._update_last_scanned"),
    ):
        scan_slack_channels.run(_WS_ID)

    mock_create.assert_not_called()
    mock_dispatch.assert_not_called()


def test_scan_embedding_failure_is_nonfatal():
    """EmbedderError during embedding should not abort the task."""
    from app.services.embedder import EmbedderError

    classify_result = _make_classify_result()
    signal_id = str(uuid4())
    mock_redis = MagicMock()
    mock_redis.set.return_value = True

    call_count = {"n": 0}

    def _run_side_effect(coro):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return classify_result  # batch_classify succeeds
        raise EmbedderError("embed failed")  # embed_texts fails

    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch(
            "app.workers.intake._fetch_all_messages",
            return_value=(
                [MagicMock(source_id="ts1")],
                {"ts1": {"_channel_id": "C001", "text": "great news", "user": "U1"}},
            ),
        ),
        patch("app.workers.intake.asyncio.run", side_effect=_run_side_effect),
        patch("app.redis_sync.get_sync_redis", return_value=mock_redis),
        patch("app.workers.intake._create_content_signal", return_value=signal_id),
        patch("app.workers.draft_pipeline.run_draft_pipeline") as mock_dispatch,
        patch("app.workers.intake._update_last_scanned"),
    ):
        scan_slack_channels.run(_WS_ID)

    # Pipeline still dispatched despite embedding failure
    mock_dispatch.assert_called_once_with(signal_id)


def test_scan_skips_pipeline_when_create_returns_none():
    """If _create_content_signal returns None, pipeline is not dispatched."""
    classify_result = _make_classify_result()
    mock_redis = MagicMock()
    mock_redis.set.return_value = True

    with (
        patch("app.workers.intake._load_workspace_row", return_value=_make_ws_settings()),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch(
            "app.workers.intake._fetch_all_messages",
            return_value=(
                [MagicMock(source_id="ts1")],
                {"ts1": {"_channel_id": "C001", "text": "great news", "user": "U1"}},
            ),
        ),
        patch("app.workers.intake.asyncio.run", return_value=classify_result),
        patch("app.workers.intake._upsert_embeddings"),
        patch("app.redis_sync.get_sync_redis", return_value=mock_redis),
        patch("app.workers.intake._create_content_signal", return_value=None),
        patch("app.workers.draft_pipeline.run_draft_pipeline") as mock_dispatch,
        patch("app.workers.intake._update_last_scanned"),
    ):
        scan_slack_channels.run(_WS_ID)

    mock_dispatch.assert_not_called()


# ---------------------------------------------------------------------------
# dispatch_intake_scans
# ---------------------------------------------------------------------------


def _mock_pool_with_rows(rows: list[tuple]):
    """Return a mock psycopg2 pool that yields the given rows from fetchall."""
    mock_cur = MagicMock()
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchall.return_value = rows

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    return mock_pool


def test_dispatch_no_eligible_workspaces():
    with (
        patch("app.db_sync.get_sync_pool", return_value=_mock_pool_with_rows([])),
        patch("app.workers.intake.scan_slack_channels") as mock_scan,
    ):
        dispatch_intake_scans.run()

    mock_scan.delay.assert_not_called()


def test_dispatch_sends_to_each_eligible_workspace():
    ws1, ws2 = str(uuid4()), str(uuid4())

    with (
        patch("app.db_sync.get_sync_pool", return_value=_mock_pool_with_rows([(ws1,), (ws2,)])),
        patch("app.workers.intake.scan_slack_channels") as mock_scan,
    ):
        dispatch_intake_scans.run()

    assert mock_scan.delay.call_count == 2
    mock_scan.delay.assert_any_call(ws1)
    mock_scan.delay.assert_any_call(ws2)


def test_dispatch_retries_on_db_error():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.side_effect = Exception("db gone")
    mock_pool.getconn.return_value = mock_conn

    with (
        patch("app.db_sync.get_sync_pool", return_value=mock_pool),
        patch("app.workers.intake.scan_slack_channels"),
        patch.object(dispatch_intake_scans, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            dispatch_intake_scans.run()
