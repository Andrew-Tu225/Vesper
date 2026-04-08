from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.draft_post import DraftPost
    from app.models.workspace import Workspace

EMBEDDING_DIM = 1536  # text-embedding-3-small


class StyleEntry(Base):
    __tablename__ = "style_entry"
    __table_args__ = (
        Index("ix_style_entry_workspace_id", "workspace_id"),
        # IVFFlat index for cosine similarity search.
        # lists=10 is appropriate for MVP scale (<1000 entries/workspace).
        # Switch to HNSW if the collection grows beyond that.
        Index(
            "ix_style_entry_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": 10},
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspace.id"), nullable=False
    )
    draft_post_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("draft_post.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=False
    )
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace")
    draft_post: Mapped[DraftPost | None] = relationship("DraftPost")
