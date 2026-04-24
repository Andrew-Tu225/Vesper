from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

# Partial unique indexes are defined in the Alembic migration, not here,
# because SQLAlchemy Index doesn't support WHERE clauses via ORM args alone.


class OAuthToken(Base, TimestampMixin):
    __tablename__ = "oauth_token"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspace.id"), nullable=False
    )
    # NULL  = workspace-level token (Slack bot)
    # SET   = user-level token (LinkedIn personal profile)
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'slack' | 'linkedin_personal'
    token_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'bot' | 'access' | 'refresh'
    encrypted_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # 12B GCM nonce
    tag: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # 16B GCM auth tag
    scopes: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace", back_populates="oauth_tokens"
    )
    user: Mapped[User | None] = relationship(
        "User", back_populates="oauth_tokens"
    )
