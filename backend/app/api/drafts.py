"""Draft action endpoints — approve, reject, rewrite content signals.

All endpoints delegate to services/approval.py (same handlers used by Slack).

POST /api/signals/{id}/approve   approve a variant + schedule
POST /api/signals/{id}/reject    reject the signal
POST /api/signals/{id}/rewrite   request a rewrite with feedback
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_workspace_for_user
from app.database import get_db
from app.models.content_signal import ContentSignal
from app.models.user import User
from app.services import approval

router = APIRouter(tags=["drafts"])

_ACTIONABLE_STATUSES = {"in_review"}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    variant_number: int
    scheduled_at: datetime
    body_override: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("scheduled_at must include a timezone offset (e.g. 2026-05-01T09:00:00+00:00)")
        return v


class RewriteRequest(BaseModel):
    variant_number: int
    feedback: str


# ---------------------------------------------------------------------------
# Private guard
# ---------------------------------------------------------------------------


async def _load_signal_for_action(
    signal_id: UUID,
    workspace_id: UUID,
    db: AsyncSession,
    *,
    require_in_review: bool = False,
) -> ContentSignal:
    """Load a ContentSignal and verify workspace ownership.

    Raises 404 if not found, 403 on workspace mismatch,
    409 if require_in_review=True and signal is not in_review.
    """
    result = await db.execute(
        select(ContentSignal).where(ContentSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()

    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")

    if signal.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if require_in_review and signal.status not in _ACTIONABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Signal is not actionable (status={signal.status})",
        )

    return signal


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/signals/{signal_id}/approve", status_code=status.HTTP_200_OK)
async def approve_signal(
    signal_id: UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Approve a draft variant and schedule it for posting.

    Accepts an optional body_override so users can make last-minute edits
    before scheduling (mirrors the editable Slack approve modal).
    """
    workspace_id = await get_workspace_for_user(user, db)
    await _load_signal_for_action(signal_id, workspace_id, db, require_in_review=True)

    await approval.handle_approve(
        signal_id=signal_id,
        variant_number=body.variant_number,
        scheduled_at=body.scheduled_at,
        actor=user.email,
        db=db,
        body_override=body.body_override,
    )
    return {"status": "ok"}


@router.post("/signals/{signal_id}/reject", status_code=status.HTTP_200_OK)
async def reject_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Reject a content signal — no post will be published."""
    workspace_id = await get_workspace_for_user(user, db)
    await _load_signal_for_action(signal_id, workspace_id, db, require_in_review=True)

    await approval.handle_reject(signal_id=signal_id, actor=user.email, db=db)
    return {"status": "ok"}


@router.post("/signals/{signal_id}/rewrite", status_code=status.HTTP_200_OK)
async def rewrite_signal(
    signal_id: UUID,
    body: RewriteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Request a rewrite of a specific draft variant with user feedback.

    Dispatches the rewrite_draft Celery task. The rewrite cap (3) is enforced
    inside the approval service.
    """
    workspace_id = await get_workspace_for_user(user, db)
    await _load_signal_for_action(signal_id, workspace_id, db, require_in_review=True)

    await approval.handle_rewrite(
        signal_id=signal_id,
        variant_number=body.variant_number,
        feedback=body.feedback,
        actor=user.email,
        db=db,
    )
    return {"status": "ok"}
