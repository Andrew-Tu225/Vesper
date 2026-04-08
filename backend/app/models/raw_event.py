from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.content_signal import ContentSignal
    from app.models.workspace import Workspace


class RawEvent(Base, TimestampMixin):
    __tablename__ = "raw_event"
    __table_args__ = (
        # Dedup: prevent duplicate events per source within the same workspace.
        # Allows re-insertion only if the prior attempt errored out.
        Index(
            "ix_raw_event_dedup",
            "workspace_id",
            "source_type",
            "source_id",
            unique=True,
            postgresql_where=text("status != 'error'"),
        ),
        Index("ix_raw_event_status_created", "status", "created_at"),
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
    )  # message_ts, email_id, etc.
    source_channel: Mapped[str | None] = mapped_column(String(255))
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    preview_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | classified_worthy | classified_noise | enriched | error
    classification: Mapped[dict | None] = mapped_column(JSONB)
    error_detail: Mapped[str | None] = mapped_column(Text)

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    content_signal: Mapped[ContentSignal | None] = relationship(
        "ContentSignal", back_populates="raw_event", uselist=False
    )
