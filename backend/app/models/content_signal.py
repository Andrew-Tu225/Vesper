from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.draft_post import DraftPost
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
    source_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # 'slack' | 'gmail'
    source_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # original message_ts, email_id, etc. — for traceability
    source_channel: Mapped[str | None] = mapped_column(String(255))
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
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # original Slack/Gmail envelope — stored only for worthy signals
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    draft_posts: Mapped[list[DraftPost]] = relationship(
        "DraftPost", back_populates="content_signal"
    )
