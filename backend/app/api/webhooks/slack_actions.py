"""Slack Interactivity webhook — receives button clicks and modal submissions
from approval cards posted to #vesper-ai.

Configure this URL in your Slack app under:
  Interactivity & Shortcuts → Request URL → POST /api/webhooks/slack/actions

Payload types handled
---------------------
block_actions    User clicked a button on an approval card.
view_submission  User submitted a modal (approve+schedule or rewrite feedback).

Action IDs (block_actions)
--------------------------
approve_signal   Open the approve+schedule datetime modal.
reject_signal    Reject the signal immediately — no post published.
rewrite_signal   Open the rewrite feedback modal.

Callback IDs (view_submission)
-------------------------------
approve_schedule  Approve variant + schedule at the chosen datetime.
rewrite_feedback  Request a rewrite with feedback text.

Button value format
-------------------
Each button encodes a JSON string in its `value` field:
    {"signal_id": "<uuid>", "variant_number": <int>}

Modal state is passed through `private_metadata` using the same JSON shape.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_slack_signature
from app.database import get_db
from app.models.workspace import Workspace
from app.services import approval
from app.services.slack_client import SlackClientError, get_workspace_client

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACTION_APPROVE = "approve_signal"
ACTION_REJECT = "reject_signal"
ACTION_REWRITE = "rewrite_signal"

CALLBACK_APPROVE_SCHEDULE = "approve_schedule"
CALLBACK_REWRITE_FEEDBACK = "rewrite_feedback"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/slack/actions", dependencies=[Depends(verify_slack_signature)])
async def slack_actions(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Receive Slack button clicks and modal submissions from approval cards.

    Always returns HTTP 200 after processing — Slack will retry on any
    non-200 response, which would cause duplicate actions.
    """
    form = await request.form()
    raw_payload = form.get("payload")
    if not raw_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payload field"
        )

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON in payload"
        )

    payload_type = payload.get("type", "")
    try:
        if payload_type == "block_actions":
            await _handle_block_action(payload, db)
        elif payload_type == "view_submission":
            await _handle_view_submission(payload, db)
        else:
            logger.warning("slack_actions: unknown payload type %r — ignoring", payload_type)
    except Exception:
        # Broad catch is intentional: never return non-200 to Slack.
        logger.exception(
            "slack_actions: unhandled error for payload type=%r", payload_type
        )

    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Block actions — button clicks
# ---------------------------------------------------------------------------


async def _handle_block_action(payload: dict, db: AsyncSession) -> None:
    """Route a button click to the appropriate handler."""
    actions = payload.get("actions", [])
    if not actions:
        return

    action = actions[0]
    action_id = action.get("action_id", "")
    actor = payload.get("user", {}).get("username", "unknown")

    try:
        value = json.loads(action.get("value", "{}"))
        signal_id = UUID(value["signal_id"])
        variant_number = int(value.get("variant_number", 1))
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning(
            "slack_actions: malformed button value %r — ignoring", action.get("value")
        )
        return

    if action_id == ACTION_REJECT:
        await approval.handle_reject(signal_id, actor, db)
        return

    if action_id in (ACTION_APPROVE, ACTION_REWRITE):
        slack_team_id = payload.get("team", {}).get("id", "")
        workspace_id = await _workspace_id_for_team(slack_team_id, db)
        if not workspace_id:
            return

        # Open modal — trigger_id expires in 3 seconds, so this runs first.
        trigger_id = payload.get("trigger_id", "")
        if action_id == ACTION_APPROVE:
            await asyncio.to_thread(
                _open_approve_modal, trigger_id, workspace_id, signal_id, variant_number
            )
        else:
            await asyncio.to_thread(
                _open_rewrite_modal, trigger_id, workspace_id, signal_id, variant_number
            )
        return

    logger.warning("slack_actions: unknown action_id %r — ignoring", action_id)


# ---------------------------------------------------------------------------
# View submissions — modal submits
# ---------------------------------------------------------------------------


async def _handle_view_submission(payload: dict, db: AsyncSession) -> None:
    """Route a modal submission to the appropriate handler."""
    callback_id = payload.get("view", {}).get("callback_id", "")
    actor = payload.get("user", {}).get("username", "unknown")

    try:
        metadata = json.loads(payload["view"]["private_metadata"])
        signal_id = UUID(metadata["signal_id"])
        variant_number = int(metadata["variant_number"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("slack_actions: malformed view private_metadata: %s", exc)
        return

    values = payload.get("view", {}).get("state", {}).get("values", {})

    if callback_id == CALLBACK_APPROVE_SCHEDULE:
        try:
            ts = values["schedule_block"]["scheduled_at_input"]["selected_date_time"]
            scheduled_at = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("slack_actions: missing scheduled_at in view submission: %s", exc)
            return
        await approval.handle_approve(signal_id, variant_number, scheduled_at, actor, db)

    elif callback_id == CALLBACK_REWRITE_FEEDBACK:
        try:
            feedback = values["feedback_block"]["feedback_input"]["value"] or ""
        except (KeyError, TypeError):
            feedback = ""
        await approval.handle_rewrite(signal_id, variant_number, feedback, actor, db)

    else:
        logger.warning("slack_actions: unknown callback_id %r — ignoring", callback_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _workspace_id_for_team(slack_team_id: str, db: AsyncSession) -> str | None:
    """Return our internal workspace UUID string for a Slack team ID.

    Returns None and logs an error if the workspace is not found.
    """
    if not slack_team_id:
        logger.error("slack_actions: missing team.id in payload")
        return None

    result = await db.execute(
        select(Workspace).where(Workspace.slack_team_id == slack_team_id)
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        logger.error("slack_actions: no workspace found for Slack team %s", slack_team_id)
        return None

    return str(workspace.id)


def _open_approve_modal(
    trigger_id: str,
    workspace_id: str,
    signal_id: UUID,
    variant_number: int,
) -> None:
    """Open the approve+schedule datetime modal in Slack.

    Sync — called via asyncio.to_thread. Trigger IDs are valid for only
    3 seconds after the button click, so this runs before any other work.
    """
    private_metadata = json.dumps(
        {"signal_id": str(signal_id), "variant_number": variant_number}
    )
    try:
        client = get_workspace_client(workspace_id)
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": CALLBACK_APPROVE_SCHEDULE,
                "title": {"type": "plain_text", "text": "Schedule Post"},
                "submit": {"type": "plain_text", "text": "Approve & Schedule"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "private_metadata": private_metadata,
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "schedule_block",
                        "label": {"type": "plain_text", "text": "When to post"},
                        "element": {
                            "type": "datetimepicker",
                            "action_id": "scheduled_at_input",
                        },
                    }
                ],
            },
        )
    except SlackClientError:
        logger.exception(
            "slack_actions: failed to open approve modal for signal %s", signal_id
        )


def _open_rewrite_modal(
    trigger_id: str,
    workspace_id: str,
    signal_id: UUID,
    variant_number: int,
) -> None:
    """Open the rewrite feedback modal in Slack.

    Sync — called via asyncio.to_thread. Trigger IDs are valid for only
    3 seconds after the button click, so this runs before any other work.
    """
    private_metadata = json.dumps(
        {"signal_id": str(signal_id), "variant_number": variant_number}
    )
    try:
        client = get_workspace_client(workspace_id)
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": CALLBACK_REWRITE_FEEDBACK,
                "title": {"type": "plain_text", "text": "Request Rewrite"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "private_metadata": private_metadata,
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "feedback_block",
                        "label": {
                            "type": "plain_text",
                            "text": "What should be changed?",
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "feedback_input",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "e.g. Make it shorter and more casual",
                            },
                        },
                    }
                ],
            },
        )
    except SlackClientError:
        logger.exception(
            "slack_actions: failed to open rewrite modal for signal %s", signal_id
        )
