from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.oauth_token import OAuthToken
    from app.models.user import User
    from app.models.workspace_member import WorkspaceMember


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspace"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    slack_team_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    linkedin_org_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    onboarding_step: Mapped[str] = mapped_column(
        String(32), nullable=False, default="connect_slack"
    )
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Billing
    subscription_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="trialing"
    )  # trialing | active | suspended | cancelled
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    owner: Mapped[User] = relationship(
        "User", back_populates="owned_workspaces", foreign_keys=[owner_user_id]
    )
    members: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember", back_populates="workspace"
    )
    oauth_tokens: Mapped[list[OAuthToken]] = relationship(
        "OAuthToken", back_populates="workspace"
    )
