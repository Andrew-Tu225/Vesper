"""Signals REST API — read-only access to ContentSignal rows.

GET /api/signals           paginated list, optional ?status= filter
GET /api/signals/{id}      signal detail with nested draft_posts
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
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
