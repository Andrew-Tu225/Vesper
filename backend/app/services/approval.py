"""Approval service — approve, reject, rewrite actions on content signals.

Called by:
- api/webhooks/slack_actions.py  (Slack button clicks + modal submissions)
- api/drafts.py                  (web Queue page REST actions — Phase 2.8)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content_signal import ContentSignal
from app.models.draft_post import DraftPost

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _load_signal(signal_id: UUID, db: AsyncSession) -> ContentSignal | None:
    """Load ContentSignal with draft_posts eagerly. Returns None if not found."""
    result = await db.execute(
        select(ContentSignal)
        .where(ContentSignal.id == signal_id)
        .options(selectinload(ContentSignal.draft_posts))
    )
    signal = result.scalar_one_or_none()
    if signal is None:
        logger.warning("approval: signal %s not found", signal_id)
    return signal


def _get_card_coords(draft_posts: list[DraftPost]) -> tuple[str, str] | None:
    """Return (slack_message_ts, slack_channel_id) from the first post that has them."""
    for dp in draft_posts:
        if dp.slack_message_ts and dp.slack_channel_id:
            return dp.slack_message_ts, dp.slack_channel_id
    return None


async def _update_slack_card(
    workspace_id: str,
    channel: str,
    ts: str,
    blocks: list[dict],
) -> None:
    """Update the Slack approval card. Non-fatal — logs on failure."""
    from app.services.slack_client import SlackClientError, get_workspace_client, update_message

    def _sync() -> None:
        client = get_workspace_client(workspace_id)
        update_message(client, channel, ts, blocks)

    try:
        await asyncio.to_thread(_sync)
    except SlackClientError:
        logger.warning("approval: failed to update Slack card ts=%s channel=%s", ts, channel)


# ---------------------------------------------------------------------------
# Status card block builders — no action buttons (card is resolved)
# ---------------------------------------------------------------------------

def _approved_blocks(summary: str, scheduled_at: datetime, actor: str) -> list[dict]:
    scheduled_str = scheduled_at.strftime("%Y-%m-%d %H:%M UTC")
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Content signal*\n{summary[:280]}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":white_check_mark: *Scheduled* for {scheduled_str} by @{actor}",
            },
        },
    ]


def _rejected_blocks(summary: str, actor: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Content signal*\n{summary[:280]}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":x: *Rejected* by @{actor}",
            },
        },
    ]


def _rewrite_blocks(summary: str, rewrite_count: int, actor: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Content signal*\n{summary[:280]}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":arrows_counterclockwise: *Rewrite requested* by @{actor} "
                    f"(attempt {rewrite_count}/3) — re-generating..."
                ),
            },
        },
    ]


def _max_rewrites_blocks(summary: str, actor: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Content signal*\n{summary[:280]}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":warning: *Max rewrites reached* (3/3) — no further rewrites allowed. Last request by @{actor}",
            },
        },
    ]


# ---------------------------------------------------------------------------
# Public handlers
# ---------------------------------------------------------------------------

async def handle_approve(
    signal_id: UUID,
    variant_number: int,
    scheduled_at: datetime,
    actor: str,
    db: AsyncSession,
    body_override: str | None = None,
) -> None:
    """Approve a draft variant and schedule it for posting.

    Marks the selected variant with is_selected=True and scheduled_at.
    Deselects all other variants. Sets signal status to 'scheduled'.
    If body_override is provided (user made edits in the approve modal),
    saves the edited text to DraftPost.body before scheduling.
    Updates the Slack approval card to a resolved state.
    """
    signal = await _load_signal(signal_id, db)
    if signal is None:
        return

    for dp in signal.draft_posts:
        dp.is_selected = dp.variant_number == variant_number
        if dp.variant_number == variant_number:
            dp.scheduled_at = scheduled_at
            if body_override:
                dp.body = body_override

    signal.status = "scheduled"
    await db.commit()

    logger.info(
        "handle_approve: signal=%s variant=%s scheduled_at=%s actor=%s",
        signal_id, variant_number, scheduled_at, actor,
    )

    coords = _get_card_coords(signal.draft_posts)
    if coords:
        ts, channel = coords
        await _update_slack_card(
            str(signal.workspace_id),
            channel,
            ts,
            _approved_blocks(signal.summary or "", scheduled_at, actor),
        )


async def handle_reject(
    signal_id: UUID,
    actor: str,
    db: AsyncSession,
) -> None:
    """Reject a content signal — no post will be published.

    Sets signal status to 'failed' and updates the Slack approval card.
    """
    signal = await _load_signal(signal_id, db)
    if signal is None:
        return

    signal.status = "failed"
    await db.commit()

    logger.info("handle_reject: signal=%s actor=%s", signal_id, actor)

    coords = _get_card_coords(signal.draft_posts)
    if coords:
        ts, channel = coords
        await _update_slack_card(
            str(signal.workspace_id),
            channel,
            ts,
            _rejected_blocks(signal.summary or "", actor),
        )


async def handle_rewrite(
    signal_id: UUID,
    variant_number: int,
    feedback: str,
    actor: str,
    db: AsyncSession,
) -> None:
    """Request a rewrite of a specific draft variant with feedback.

    Stores feedback on the target DraftPost, increments rewrite_count in
    metadata_, enforces a cap of 3, and dispatches the rewrite_draft Celery
    task which applies the feedback via GPT-4o and posts a new approval card.
    """
    signal = await _load_signal(signal_id, db)
    if signal is None:
        return

    rewrite_count = signal.metadata_.get("rewrite_count", 0) + 1
    coords = _get_card_coords(signal.draft_posts)

    if rewrite_count > 3:
        logger.warning(
            "handle_rewrite: cap exceeded for signal=%s actor=%s", signal_id, actor
        )
        if coords:
            ts, channel = coords
            await _update_slack_card(
                str(signal.workspace_id),
                channel,
                ts,
                _max_rewrites_blocks(signal.summary or "", actor),
            )
        return

    for dp in signal.draft_posts:
        if dp.variant_number == variant_number:
            dp.feedback = feedback

    # Full dict reassignment required — SQLAlchemy does not detect nested JSONB mutations
    signal.metadata_ = {**signal.metadata_, "rewrite_count": rewrite_count}
    await db.commit()

    logger.info(
        "handle_rewrite: signal=%s variant=%s count=%s actor=%s",
        signal_id, variant_number, rewrite_count, actor,
    )

    # Update card to "re-generating..." before dispatching the task so the card
    # always reflects the in-progress state before the revised content arrives.
    if coords:
        ts, channel = coords
        await _update_slack_card(
            str(signal.workspace_id),
            channel,
            ts,
            _rewrite_blocks(signal.summary or "", rewrite_count, actor),
        )

    # Deferred import breaks the workers → services potential cycle
    from app.workers.draft_pipeline import rewrite_draft
    rewrite_draft.delay(str(signal_id), variant_number)
