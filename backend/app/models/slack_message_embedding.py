from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace

EMBEDDING_DIM = 1536  # text-embedding-3-small


class SlackMessageEmbedding(Base):
    """Embedded Slack messages stored for enrichment context retrieval.

    The intake scanner writes one row per message the batch classifier flags
    in embed_message_ids. The enrichment agent (enrich_context) queries this
    table via cosine similarity to find related context that may span multiple
    days of conversation — beyond what a single scan window can see.

    Rows older than 30 days are deleted by the maintenance task
    purge_slack_message_embeddings — old messages lose relevance as context.

    No updated_at — rows are write-once and never mutated after insert.
    """

    __tablename__ = "slack_message_embedding"
    __table_args__ = (
        # Dedup: same message arriving in two overlapping scan windows is a no-op.
        Index(
            "uq_slack_msg_embedding_ts",
            "workspace_id",
            "channel_id",
            "message_ts",
            unique=True,
        ),
        Index("ix_slack_msg_embedding_workspace", "workspace_id"),
        # Used by the TTL cleanup task to efficiently delete old rows.
        Index("ix_slack_msg_embedding_stored_at", "stored_at"),
        # IVFFlat for cosine similarity search.
        # lists=10 is appropriate for <100k rows per workspace at pilot scale.
        Index(
            "ix_slack_msg_embedding_ivfflat",
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
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    message_ts: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Slack message timestamp — dedup anchor and provenance for enrichment results",
    )
    author_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When this row was inserted — used for 30-day TTL cleanup",
    )

    workspace: Mapped[Workspace] = relationship("Workspace")
