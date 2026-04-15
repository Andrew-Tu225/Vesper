"""Approval service — approve, reject, rewrite actions on content signals.

Called by:
- api/webhooks/slack_actions.py  (Slack button clicks + modal submissions)
- api/drafts.py                  (web Queue page REST actions — Phase 2.8)

Phase 2.4: stubs — log and no-op.
Phase 2.7: full implementation (DB writes + Slack card updates).
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def handle_approve(
    signal_id: UUID,
    variant_number: int,
    scheduled_at: datetime,
    actor: str,
    db: AsyncSession,
) -> None:
    """Approve a draft variant and schedule it for posting.

    Sets DraftPost.is_selected = True, DraftPost.scheduled_at = scheduled_at,
    ContentSignal.status = 'scheduled', and updates the Slack approval card.

    Phase 2.7 implementation.
    """
    logger.warning(
        "handle_approve: not yet implemented (Phase 2.7) — "
        "signal_id=%s variant=%s actor=%s scheduled_at=%s",
        signal_id,
        variant_number,
        actor,
        scheduled_at,
    )


async def handle_reject(
    signal_id: UUID,
    actor: str,
    db: AsyncSession,
) -> None:
    """Reject a content signal — no post will be published.

    Sets ContentSignal.status = 'failed' and updates the Slack approval card.

    Phase 2.7 implementation.
    """
    logger.warning(
        "handle_reject: not yet implemented (Phase 2.7) — signal_id=%s actor=%s",
        signal_id,
        actor,
    )


async def handle_rewrite(
    signal_id: UUID,
    variant_number: int,
    feedback: str,
    actor: str,
    db: AsyncSession,
) -> None:
    """Request a rewrite of a specific draft variant with feedback.

    Stores feedback on the target DraftPost, checks rewrite_count <= 3,
    re-dispatches generate_draft for that variant only, and updates the
    Slack approval card.

    Phase 2.7 implementation.
    """
    logger.warning(
        "handle_rewrite: not yet implemented (Phase 2.7) — "
        "signal_id=%s variant=%s actor=%s feedback=%r",
        signal_id,
        variant_number,
        actor,
        feedback,
    )
