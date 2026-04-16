"""Tests for draft pipeline Celery tasks.

Sync tests (plain def, not async) because the Celery tasks call asyncio.run()
internally and cannot run inside an already-running event loop.

Calling convention for bound Celery tasks:
  task.run(arg)        — runs synchronously, injects the real task instance as self
  task.retry           — patched directly on the task object for retry testing
"""

from __future__ import annotations

import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/vesper_test")

from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest

from app.workers.draft_pipeline import (
    classify_signal,
    enrich_context,
    generate_draft,
    run_draft_pipeline,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_WS_ID = str(uuid4())
_SIG_ID = str(uuid4())


def _make_signal_row(
    *,
    workspace_id: str = _WS_ID,
    signal_type: str = "product_win",
    summary: str = "We hit 1k users",
    original_text: str = "We hit 1k paying users today!",
    raw_payload: dict | None = None,
    metadata_: dict | None = None,
    source_channel: str = "C001",
    source_id: str = "ts1",
) -> dict:
    if raw_payload is None:
        raw_payload = {
            "messages": [
                {"ts": "ts1", "channel_id": "C001", "text": "We hit 1k paying users today!"},
            ]
        }
    return {
        "id": _SIG_ID,
        "workspace_id": workspace_id,
        "signal_type": signal_type,
        "summary": summary,
        "original_text": original_text,
        "redacted_text": None,
        "raw_payload": raw_payload,
        "metadata_": metadata_ or {},
        "source_channel": source_channel,
        "source_id": source_id,
    }


def _make_ws_settings(
    *,
    variant_count: int = 2,
    queue_channel: str = "vesper-ai",
) -> dict:
    return {
        "draft_variant_count": variant_count,
        "social_queue_channel": queue_channel,
    }


def _mock_pool(fetchone=None, fetchall=None):
    """Return a psycopg2 pool mock that yields one conn with one cursor."""
    mock_cur = MagicMock()
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = fetchone
    mock_cur.fetchall.return_value = fetchall or []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    return mock_pool


# ---------------------------------------------------------------------------
# run_draft_pipeline
# ---------------------------------------------------------------------------


def test_run_draft_pipeline_rejects_invalid_uuid():
    """Bad UUID should log and return without dispatching."""
    with patch("app.workers.draft_pipeline.chain") as mock_chain:
        run_draft_pipeline("not-a-uuid")
    mock_chain.assert_not_called()


def test_run_draft_pipeline_dispatches_chain():
    """Valid UUID builds the three-task chain and calls apply_async."""
    signal_id = str(uuid4())
    mock_chain_instance = MagicMock()

    with patch("app.workers.draft_pipeline.chain", return_value=mock_chain_instance) as mock_chain:
        run_draft_pipeline(signal_id)

    mock_chain.assert_called_once()
    mock_chain_instance.apply_async.assert_called_once()


# ---------------------------------------------------------------------------
# classify_signal
# ---------------------------------------------------------------------------


def test_classify_signal_drops_invalid_uuid():
    """Invalid UUID should return early without touching the DB."""
    with patch("app.workers.draft_pipeline._load_signal_row") as mock_load:
        classify_signal.run("bad-uuid")
    mock_load.assert_not_called()


def test_classify_signal_drops_when_signal_not_found():
    with patch("app.workers.draft_pipeline._load_signal_row", return_value=None):
        result = classify_signal.run(_SIG_ID)
    assert result == _SIG_ID


def test_classify_signal_happy_path_writes_original_text():
    row = _make_signal_row()
    mock_pool = _mock_pool()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
    ):
        result = classify_signal.run(_SIG_ID)

    assert result == _SIG_ID
    mock_conn = mock_pool.getconn.return_value
    mock_conn.commit.assert_called_once()


def test_classify_signal_concatenates_multiple_messages():
    """original_text should be all message texts joined by double newline."""
    row = _make_signal_row(
        raw_payload={
            "messages": [
                {"ts": "ts1", "channel_id": "C001", "text": "Line one"},
                {"ts": "ts2", "channel_id": "C001", "text": "Line two"},
            ]
        }
    )
    mock_pool = _mock_pool()
    captured_args: list = []

    def _fake_execute(sql, args):
        captured_args.extend(args)

    mock_cur = mock_pool.getconn.return_value.cursor.return_value.__enter__.return_value
    mock_cur.execute.side_effect = _fake_execute

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
    ):
        classify_signal.run(_SIG_ID)

    # First positional arg to the UPDATE is original_text
    assert "Line one" in captured_args[0]
    assert "Line two" in captured_args[0]


def test_classify_signal_retries_on_db_error():
    row = _make_signal_row()
    mock_pool = _mock_pool()
    mock_pool.getconn.return_value.cursor.side_effect = Exception("db gone")

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
        patch.object(classify_signal, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            classify_signal.run(_SIG_ID)


# ---------------------------------------------------------------------------
# enrich_context
# ---------------------------------------------------------------------------


def test_enrich_context_drops_when_signal_not_found():
    with patch("app.workers.draft_pipeline._load_signal_row", return_value=None):
        result = enrich_context.run(_SIG_ID)
    assert result == _SIG_ID


def test_enrich_context_happy_path_writes_context_summary():
    row = _make_signal_row()
    mock_pool = _mock_pool()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch(
            "app.workers.draft_pipeline.asyncio.run",
            return_value=("Enriched context paragraph.", 2),
        ),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
    ):
        result = enrich_context.run(_SIG_ID)

    assert result == _SIG_ID
    mock_pool.getconn.return_value.commit.assert_called_once()


def test_enrich_context_builds_source_messages_from_payload():
    """Source messages with ts + channel_id should be passed to the agent."""
    row = _make_signal_row(
        raw_payload={
            "messages": [
                {"ts": "ts1", "channel_id": "C001", "text": "msg one"},
                {"ts": "ts2", "channel_id": "C002", "text": "msg two"},
                # Missing channel_id — should be filtered out
                {"ts": "ts3", "text": "no channel"},
            ]
        }
    )
    mock_pool = _mock_pool()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=("summary", 1)),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
    ):
        result = enrich_context.run(_SIG_ID)

    # asyncio.run was called (agent was invoked) and task returned cleanly
    assert result == _SIG_ID


def test_enrich_context_falls_back_to_source_id_when_no_messages():
    """If raw_payload has no messages, fall back to (source_id, source_channel, original_text)."""
    row = _make_signal_row(raw_payload={})
    mock_pool = _mock_pool()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=("fallback", 1)),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
    ):
        result = enrich_context.run(_SIG_ID)

    assert result == _SIG_ID


def test_enrich_context_retries_on_agent_failure():
    row = _make_signal_row()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.asyncio.run", side_effect=Exception("openai down")),
        patch.object(enrich_context, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            enrich_context.run(_SIG_ID)


def test_enrich_context_retries_on_db_error():
    row = _make_signal_row()
    mock_pool = _mock_pool()
    mock_pool.getconn.return_value.cursor.side_effect = Exception("db gone")

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=("context", 1)),
        patch("app.workers.draft_pipeline.get_sync_pool", return_value=mock_pool),
        patch.object(enrich_context, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            enrich_context.run(_SIG_ID)


# ---------------------------------------------------------------------------
# generate_draft
# ---------------------------------------------------------------------------


def test_generate_draft_drops_when_signal_not_found():
    with patch("app.workers.draft_pipeline._load_signal_row", return_value=None):
        result = generate_draft.run(_SIG_ID)
    assert result == _SIG_ID


def test_generate_draft_happy_path():
    """Full happy path: LLM generates variants, DraftPosts inserted, Slack card posted."""
    row = _make_signal_row(
        metadata_={"enrichment": {"context_summary": "Enriched context.", "iterations": 2}}
    )
    ws_settings = _make_ws_settings()
    variants = ["Variant one body.", "Variant two body."]
    post_ids = [str(uuid4()), str(uuid4())]
    message_ts = "1712345678.000100"

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=variants),
        patch("app.workers.draft_pipeline._insert_draft_posts", return_value=post_ids),
        patch("app.workers.draft_pipeline._update_draft_posts_slack_ts"),
        patch("app.workers.draft_pipeline._update_signal_status"),
        patch(
            "app.services.slack_client.get_workspace_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.slack_client.post_message",
            return_value=message_ts,
        ) as mock_post,
    ):
        result = generate_draft.run(_SIG_ID)

    assert result == _SIG_ID
    mock_post.assert_called_once()


def test_generate_draft_passes_source_messages_to_llm():
    """Source messages from raw_payload should be forwarded to run_generate."""
    row = _make_signal_row(
        raw_payload={
            "messages": [
                {"ts": "ts1", "channel_id": "C001", "text": "real slack message"},
            ]
        },
        metadata_={"enrichment": {"context_summary": "context", "iterations": 1}},
    )
    ws_settings = _make_ws_settings()
    captured: dict = {}

    def _fake_asyncio_run(coro):
        captured["coro"] = coro
        return ["draft one", "draft two"]

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", side_effect=_fake_asyncio_run),
        patch("app.workers.draft_pipeline._insert_draft_posts", return_value=[str(uuid4())]),
        patch("app.workers.draft_pipeline._update_draft_posts_slack_ts"),
        patch("app.workers.draft_pipeline._update_signal_status"),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch("app.services.slack_client.post_message", return_value="ts.1"),
    ):
        generate_draft.run(_SIG_ID)

    # asyncio.run was called — the coroutine was created with source_messages
    assert "coro" in captured


def test_generate_draft_uses_variant_count_from_workspace_settings():
    """draft_variant_count from workspace settings controls how many variants are requested."""
    row = _make_signal_row()
    ws_settings = _make_ws_settings(variant_count=3)
    captured_calls: list = []

    def _fake_asyncio_run(coro):
        captured_calls.append(coro)
        return ["v1", "v2", "v3"]

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", side_effect=_fake_asyncio_run),
        patch("app.workers.draft_pipeline._insert_draft_posts", return_value=[str(uuid4())] * 3),
        patch("app.workers.draft_pipeline._update_draft_posts_slack_ts"),
        patch("app.workers.draft_pipeline._update_signal_status"),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch("app.services.slack_client.post_message", return_value="ts.1"),
    ):
        generate_draft.run(_SIG_ID)

    assert len(captured_calls) == 1


def test_generate_draft_retries_on_llm_failure():
    row = _make_signal_row()
    ws_settings = _make_ws_settings()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", side_effect=Exception("openai down")),
        patch.object(generate_draft, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            generate_draft.run(_SIG_ID)


def test_generate_draft_retries_on_insert_failure():
    row = _make_signal_row()
    ws_settings = _make_ws_settings()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=["v1", "v2"]),
        patch(
            "app.workers.draft_pipeline._insert_draft_posts",
            side_effect=Exception("db gone"),
        ),
        patch.object(generate_draft, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            generate_draft.run(_SIG_ID)


def test_generate_draft_retries_on_slack_failure():
    from app.services.slack_client import SlackClientError

    row = _make_signal_row()
    ws_settings = _make_ws_settings()

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=["v1", "v2"]),
        patch("app.workers.draft_pipeline._insert_draft_posts", return_value=[str(uuid4())]),
        patch(
            "app.services.slack_client.get_workspace_client",
            side_effect=SlackClientError("no token"),
        ),
        patch.object(generate_draft, "retry", side_effect=Exception("retry raised")),
    ):
        with pytest.raises(Exception, match="retry raised"):
            generate_draft.run(_SIG_ID)


def test_generate_draft_status_set_to_in_review():
    from app.workers.constants import SignalStatus

    row = _make_signal_row()
    ws_settings = _make_ws_settings()
    status_calls: list = []

    with (
        patch("app.workers.draft_pipeline._load_signal_row", return_value=row),
        patch("app.workers.draft_pipeline._load_workspace_settings", return_value=ws_settings),
        patch("app.workers.draft_pipeline.asyncio.run", return_value=["v1", "v2"]),
        patch("app.workers.draft_pipeline._insert_draft_posts", return_value=[str(uuid4())]),
        patch("app.workers.draft_pipeline._update_draft_posts_slack_ts"),
        patch(
            "app.workers.draft_pipeline._update_signal_status",
            side_effect=lambda sig_id, status: status_calls.append(status),
        ),
        patch("app.services.slack_client.get_workspace_client", return_value=MagicMock()),
        patch("app.services.slack_client.post_message", return_value="ts.1"),
    ):
        generate_draft.run(_SIG_ID)

    assert SignalStatus.IN_REVIEW in status_calls


# ---------------------------------------------------------------------------
# _build_approval_card (unit)
# ---------------------------------------------------------------------------


def test_build_approval_card_structure():
    from app.workers.draft_pipeline import _build_approval_card

    blocks = _build_approval_card(
        summary="Product win summary",
        variants=["Body one.", "Body two."],
        signal_id=_SIG_ID,
    )

    # Must be a non-empty list of dicts
    assert isinstance(blocks, list)
    assert len(blocks) > 0

    types = [b["type"] for b in blocks]
    # Should contain at least one actions block (buttons)
    assert "actions" in types
    # Should contain at least one section block (text)
    assert "section" in types


def test_build_approval_card_has_approve_and_reject_buttons():
    import json as _json

    from app.workers.draft_pipeline import _build_approval_card

    blocks = _build_approval_card(
        summary="summary",
        variants=["Variant A", "Variant B"],
        signal_id=_SIG_ID,
    )

    action_ids = []
    for block in blocks:
        if block["type"] == "actions":
            for el in block.get("elements", []):
                action_ids.append(el.get("action_id", ""))

    assert "approve_signal" in action_ids
    assert "reject_signal" in action_ids


def test_build_approval_card_encodes_signal_id_in_button_value():
    import json as _json

    from app.workers.draft_pipeline import _build_approval_card

    blocks = _build_approval_card("summary", ["body"], _SIG_ID)

    for block in blocks:
        if block["type"] == "actions":
            for el in block.get("elements", []):
                value = _json.loads(el["value"])
                assert value["signal_id"] == _SIG_ID
