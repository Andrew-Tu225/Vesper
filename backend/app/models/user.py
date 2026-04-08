from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.oauth_token import OAuthToken
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Relationships
    owned_workspaces: Mapped[list[Workspace]] = relationship(
        "Workspace", back_populates="owner", foreign_keys="Workspace.owner_user_id"
    )
    memberships: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        foreign_keys="WorkspaceMember.user_id",
    )
    oauth_tokens: Mapped[list[OAuthToken]] = relationship(
        "OAuthToken", back_populates="user"
    )
