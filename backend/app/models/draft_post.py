from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.content_signal import ContentSignal
    from app.models.user import User
    from app.models.workspace import Workspace


class DraftPost(Base, TimestampMixin):
    __tablename__ = "draft_post"
    __table_args__ = (
        # Fast lookup of selected posts that are ready to schedule/publish
        Index(
            "ix_draft_post_scheduled",
            "scheduled_at",
            postgresql_where=text("is_selected = TRUE AND published_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_signal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("content_signal.id"), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id"),
        nullable=False,
    )  # denormalized for query convenience
    variant_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    slack_message_ts: Mapped[str | None] = mapped_column(String(64))
    slack_channel_id: Mapped[str | None] = mapped_column(String(64))
    # Publish target — set when the draft is approved
    publish_target: Mapped[str | None] = mapped_column(
        String(32)
    )  # 'company_page' | 'personal'
    publisher_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )  # which user's personal LinkedIn (null for company_page)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    linkedin_post_id: Mapped[str | None] = mapped_column(String(128))

    # Relationships
    content_signal: Mapped[ContentSignal] = relationship(
        "ContentSignal", back_populates="draft_posts"
    )
    workspace: Mapped[Workspace] = relationship("Workspace")
    publisher: Mapped[User | None] = relationship(
        "User", foreign_keys=[publisher_user_id]
    )
