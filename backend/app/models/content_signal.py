from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.draft_post import DraftPost
    from app.models.raw_event import RawEvent
    from app.models.workspace import Workspace


class ContentSignal(Base, TimestampMixin):
    __tablename__ = "content_signal"
    __table_args__ = (
        Index("ix_content_signal_workspace_status", "workspace_id", "status"),
        Index("ix_content_signal_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspace.id"), nullable=False
    )
    raw_event_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("raw_event.id"), unique=True, nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # 'slack' | 'gmail'
    signal_type: Mapped[str | None] = mapped_column(
        String(32)
    )  # customer_praise | product_win | launch_update | hiring | founder_insight
    original_text: Mapped[str | None] = mapped_column(Text)
    redacted_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown"
    )  # unknown | low | medium | high
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="detected"
    )  # detected | drafted | in_review | approved | scheduled | posted
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    raw_event: Mapped[RawEvent] = relationship(
        "RawEvent", back_populates="content_signal"
    )
    draft_posts: Mapped[list[DraftPost]] = relationship(
        "DraftPost", back_populates="content_signal"
    )
