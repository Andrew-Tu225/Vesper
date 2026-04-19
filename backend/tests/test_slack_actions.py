"""Tests for the Slack interactive actions webhook."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.deps import verify_slack_signature
from app.api.webhooks.slack_actions import (
    ACTION_APPROVE,
    ACTION_REJECT,
    ACTION_REWRITE,
    CALLBACK_APPROVE_SCHEDULE,
    CALLBACK_REWRITE_FEEDBACK,
)
from app.main import app
from app.models.workspace import Workspace


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SIGNAL_ID = str(uuid4())
_VARIANT = 1
_ACTOR = "john"
_BUTTON_VALUE = json.dumps({"signal_id": _SIGNAL_ID, "variant_number": _VARIANT})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def no_sig_check():
    """Override Slack signature verification to a no-op for happy path tests."""
    app.dependency_overrides[verify_slack_signature] = lambda: None
    yield
    app.dependency_overrides.pop(verify_slack_signature, None)


def _block_action_payload(action_id: str, value: str = _BUTTON_VALUE) -> str:
    return json.dumps({
        "type": "block_actions",
        "team": {"id": "T123456"},
        "user": {"id": "U123", "username": _ACTOR},
        "trigger_id": "trigger-abc123",
        "actions": [{"action_id": action_id, "value": value, "block_id": "b1"}],
    })


def _view_submission_payload(
    callback_id: str,
    state_values: dict,
    metadata: dict | None = None,
) -> str:
    meta = metadata or {"signal_id": _SIGNAL_ID, "variant_number": _VARIANT}
    return json.dumps({
        "type": "view_submission",
        "team": {"id": "T123456"},
        "user": {"id": "U123", "username": _ACTOR},
        "view": {
            "callback_id": callback_id,
            "private_metadata": json.dumps(meta),
            "state": {"values": state_values},
        },
    })


def _make_workspace(slack_team_id: str = "T123456") -> Workspace:
    return Workspace(
        id=uuid4(),
        name="Acme Corp",
        owner_user_id=uuid4(),
        slack_team_id=slack_team_id,
    )


def _seed_workspace(mock_db: AsyncMock, workspace: Workspace) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = workspace
    mock_db.execute = AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


async def test_missing_signature_headers_returns_422(client):
    resp = await client.post(
        "/api/webhooks/slack/actions",
        data={"payload": _block_action_payload(ACTION_REJECT)},
    )
    assert resp.status_code == 422


async def test_invalid_signature_returns_401(client):
    resp = await client.post(
        "/api/webhooks/slack/actions",
        data={"payload": _block_action_payload(ACTION_REJECT)},
        headers={
            "x-slack-request-timestamp": str(int(time.time())),
            "x-slack-signature": "v0=invalidsignature",
        },
    )
    assert resp.status_code == 401


async def test_stale_timestamp_returns_401(client):
    stale = str(int(time.time()) - 400)  # beyond 300s tolerance
    resp = await client.post(
        "/api/webhooks/slack/actions",
        data={"payload": _block_action_payload(ACTION_REJECT)},
        headers={
            "x-slack-request-timestamp": stale,
            "x-slack-signature": "v0=anything",
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


async def test_missing_payload_field_returns_400(client, no_sig_check):
    resp = await client.post("/api/webhooks/slack/actions", data={})
    assert resp.status_code == 400


async def test_invalid_json_payload_returns_400(client, no_sig_check):
    resp = await client.post(
        "/api/webhooks/slack/actions", data={"payload": "not-json"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# block_actions — button clicks
# ---------------------------------------------------------------------------


async def test_reject_signal_calls_handle_reject(client, mock_db, no_sig_check):
    with patch(
        "app.api.webhooks.slack_actions.approval.handle_reject",
        new_callable=AsyncMock,
    ) as mock_reject:
        resp = await client.post(
            "/api/webhooks/slack/actions",
            data={"payload": _block_action_payload(ACTION_REJECT)},
        )

    assert resp.status_code == 200
    mock_reject.assert_awaited_once()
    args = mock_reject.call_args[0]
    assert str(args[0]) == _SIGNAL_ID  # signal_id
    assert args[1] == _ACTOR           # actor


async def test_approve_signal_opens_approve_modal(client, mock_db, no_sig_check):
    workspace = _make_workspace()

    # First execute call: _workspace_id_for_team returns Workspace
    workspace_result = MagicMock()
    workspace_result.scalar_one_or_none.return_value = workspace

    # Second execute call: _fetch_draft_body returns a DraftPost with body
    draft = MagicMock()
    draft.body = "The draft post body"
    draft_result = MagicMock()
    draft_result.scalar_one_or_none.return_value = draft

    mock_db.execute = AsyncMock(side_effect=[workspace_result, draft_result])

    with patch("app.api.webhooks.slack_actions._open_approve_modal") as mock_open:
        resp = await client.post(
            "/api/webhooks/slack/actions",
            data={"payload": _block_action_payload(ACTION_APPROVE)},
        )

    assert resp.status_code == 200
    mock_open.assert_called_once()
    args = mock_open.call_args[0]
    assert args[0] == "trigger-abc123"        # trigger_id
    assert args[1] == str(workspace.id)       # workspace_id
    assert str(args[2]) == _SIGNAL_ID         # signal_id
    assert args[3] == _VARIANT                # variant_number
    assert args[4] == "The draft post body"   # draft_body


async def test_rewrite_signal_opens_rewrite_modal(client, mock_db, no_sig_check):
    workspace = _make_workspace()
    _seed_workspace(mock_db, workspace)

    with patch("app.api.webhooks.slack_actions._open_rewrite_modal") as mock_open:
        resp = await client.post(
            "/api/webhooks/slack/actions",
            data={"payload": _block_action_payload(ACTION_REWRITE)},
        )

    assert resp.status_code == 200
    mock_open.assert_called_once()
    args = mock_open.call_args[0]
    assert args[0] == "trigger-abc123"
    assert args[1] == str(workspace.id)
    assert str(args[2]) == _SIGNAL_ID


async def test_unknown_action_id_returns_200(client, mock_db, no_sig_check):
    resp = await client.post(
        "/api/webhooks/slack/actions",
        data={"payload": _block_action_payload("unknown_action_xyz")},
    )
    assert resp.status_code == 200


async def test_unknown_payload_type_returns_200(client, no_sig_check):
    resp = await client.post(
        "/api/webhooks/slack/actions",
        data={"payload": json.dumps({"type": "unknown_type"})},
    )
    assert resp.status_code == 200


async def test_approve_without_workspace_returns_200(client, mock_db, no_sig_check):
    """If workspace lookup fails, the endpoint still returns 200 (no modal opened)."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    with patch("app.api.webhooks.slack_actions._open_approve_modal") as mock_open:
        resp = await client.post(
            "/api/webhooks/slack/actions",
            data={"payload": _block_action_payload(ACTION_APPROVE)},
        )

    assert resp.status_code == 200
    mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# view_submission — modal submits
# ---------------------------------------------------------------------------


async def test_approve_schedule_calls_handle_approve(client, mock_db, no_sig_check):
    scheduled_ts = 1712500000
    state = {
        "schedule_block": {
            "scheduled_at_input": {
                "type": "datetimepicker",
                "selected_date_time": scheduled_ts,
            }
        }
    }

    with patch(
        "app.api.webhooks.slack_actions.approval.handle_approve",
        new_callable=AsyncMock,
    ) as mock_approve:
        resp = await client.post(
            "/api/webhooks/slack/actions",
            data={"payload": _view_submission_payload(CALLBACK_APPROVE_SCHEDULE, state)},
        )

    assert resp.status_code == 200
    mock_approve.assert_awaited_once()
    args = mock_approve.call_args[0]
    assert str(args[0]) == _SIGNAL_ID                                          # signal_id
    assert args[1] == _VARIANT                                                 # variant_number
    assert args[2] == datetime.fromtimestamp(scheduled_ts, tz=timezone.utc)   # scheduled_at
    assert args[3] == _ACTOR                                                   # actor


async def test_rewrite_feedback_calls_handle_rewrite(client, mock_db, no_sig_check):
    state = {
        "feedback_block": {
            "feedback_input": {"type": "plain_text_input", "value": "Make it shorter"}
        }
    }

    with patch(
        "app.api.webhooks.slack_actions.approval.handle_rewrite",
        new_callable=AsyncMock,
    ) as mock_rewrite:
        resp = await client.post(
            "/api/webhooks/slack/actions",
            data={"payload": _view_submission_payload(CALLBACK_REWRITE_FEEDBACK, state)},
        )

    assert resp.status_code == 200
    mock_rewrite.assert_awaited_once()
    args = mock_rewrite.call_args[0]
    assert str(args[0]) == _SIGNAL_ID   # signal_id
    assert args[1] == _VARIANT          # variant_number
    assert args[2] == "Make it shorter" # feedback
    assert args[3] == _ACTOR            # actor


async def test_unknown_callback_id_returns_200(client, mock_db, no_sig_check):
    resp = await client.post(
        "/api/webhooks/slack/actions",
        data={
            "payload": _view_submission_payload(
                "unknown_callback", {}, {"signal_id": _SIGNAL_ID, "variant_number": 1}
            )
        },
    )
    assert resp.status_code == 200
