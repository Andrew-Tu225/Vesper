"""Signals REST API — read-only access to ContentSignal rows.

GET /api/signals           paginated list, optional ?status= filter
GET /api/signals/stats     aggregate stats for the dashboard
GET /api/signals/{id}      signal detail with nested draft_posts
"""

from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_workspace_for_user
from app.database import get_db
from app.models.content_signal import ContentSignal
from app.models.draft_post import DraftPost
from app.models.user import User

router = APIRouter(tags=["signals"])

_MAX_LIMIT = 100


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DraftPostOut(BaseModel):
    id: UUID
    variant_number: int
    body: str
    is_selected: bool
    feedback: str | None
    scheduled_at: datetime | None
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListItem(BaseModel):
    id: UUID
    signal_type: str | None
    summary: str | None
    status: str
    source_type: str
    source_channel: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    signals: list[SignalListItem]
    total: int
    page: int
    limit: int


class SignalDetailResponse(BaseModel):
    id: UUID
    signal_type: str | None
    summary: str | None
    status: str
    source_type: str
    source_channel: str | None
    created_at: datetime
    draft_posts: list[DraftPostOut]

    model_config = {"from_attributes": True}


class ClassificationBucket(BaseModel):
    signal_type: str
    count: int
    percent: int


class SignalStatsResponse(BaseModel):
    total_signals_this_week: int
    drafts_awaiting_review: int
    posts_published_this_month: int
    classification_mix: list[ClassificationBucket]


_CANONICAL_SIGNAL_TYPES = [
    "customer_praise",
    "product_win",
    "hiring",
    "launch_update",
    "founder_insight",
]


def _largest_remainder_percents(counts: dict[str, int]) -> dict[str, int]:
    """Convert raw counts to integers that sum to exactly 100 using largest-remainder."""
    total = sum(counts.values())
    if total == 0:
        return {k: 0 for k in counts}

    raw = {k: v / total * 100 for k, v in counts.items()}
    floors = {k: math.floor(v) for k, v in raw.items()}
    remainder = 100 - sum(floors.values())

    # Distribute leftover points to types with largest fractional parts
    by_remainder = sorted(counts.keys(), key=lambda k: raw[k] - floors[k], reverse=True)
    for k in by_remainder[:remainder]:
        floors[k] += 1

    return floors


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/signals", response_model=SignalListResponse)
async def list_signals(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=_MAX_LIMIT),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SignalListResponse:
    """List content signals for the authenticated user's workspace.

    Results are ordered by created_at DESC. Supports optional ?status= filter
    and pagination via ?page= and ?limit= query params.
    """
    workspace_id = await get_workspace_for_user(user, db)

    base_filter = [ContentSignal.workspace_id == workspace_id]
    if status_filter:
        base_filter.append(ContentSignal.status == status_filter)

    total_result = await db.execute(
        select(func.count()).select_from(ContentSignal).where(*base_filter)
    )
    total = total_result.scalar_one()

    offset = (page - 1) * limit
    rows_result = await db.execute(
        select(ContentSignal)
        .where(*base_filter)
        .order_by(ContentSignal.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    signals = rows_result.scalars().all()

    return SignalListResponse(
        signals=[SignalListItem.model_validate(s) for s in signals],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/signals/stats", response_model=SignalStatsResponse)
async def get_signal_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SignalStatsResponse:
    """Return aggregate stats for the authenticated user's workspace."""
    workspace_id = await get_workspace_for_user(user, db)

    week_result = await db.execute(
        select(func.count())
        .select_from(ContentSignal)
        .where(
            ContentSignal.workspace_id == workspace_id,
            ContentSignal.created_at >= func.now() - text("interval '7 days'"),
        )
    )
    total_signals_this_week = week_result.scalar_one()

    review_result = await db.execute(
        select(func.count())
        .select_from(ContentSignal)
        .where(
            ContentSignal.workspace_id == workspace_id,
            ContentSignal.status == "in_review",
        )
    )
    drafts_awaiting_review = review_result.scalar_one()

    month_result = await db.execute(
        select(func.count())
        .select_from(ContentSignal)
        .where(
            ContentSignal.workspace_id == workspace_id,
            ContentSignal.status == "posted",
            ContentSignal.created_at >= func.now() - text("interval '30 days'"),
        )
    )
    posts_published_this_month = month_result.scalar_one()

    mix_result = await db.execute(
        select(ContentSignal.signal_type, func.count().label("cnt"))
        .where(
            ContentSignal.workspace_id == workspace_id,
            ContentSignal.signal_type.isnot(None),
        )
        .group_by(ContentSignal.signal_type)
    )
    raw_counts: dict[str, int] = {row.signal_type: row.cnt for row in mix_result}
    counts = {t: raw_counts.get(t, 0) for t in _CANONICAL_SIGNAL_TYPES}
    percents = _largest_remainder_percents(counts)

    classification_mix = [
        ClassificationBucket(signal_type=t, count=counts[t], percent=percents[t])
        for t in _CANONICAL_SIGNAL_TYPES
    ]

    return SignalStatsResponse(
        total_signals_this_week=total_signals_this_week,
        drafts_awaiting_review=drafts_awaiting_review,
        posts_published_this_month=posts_published_this_month,
        classification_mix=classification_mix,
    )


@router.get("/signals/{signal_id}", response_model=SignalDetailResponse)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SignalDetailResponse:
    """Return a single content signal with all its draft_posts.

    Raises 404 if the signal does not exist.
    Raises 403 if the signal belongs to a different workspace.
    """
    workspace_id = await get_workspace_for_user(user, db)

    result = await db.execute(
        select(ContentSignal)
        .where(ContentSignal.id == signal_id)
        .options(selectinload(ContentSignal.draft_posts))
    )
    signal = result.scalar_one_or_none()

    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")

    if signal.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return SignalDetailResponse.model_validate(signal)
