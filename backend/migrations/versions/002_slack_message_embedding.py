"""slack_message_embedding table

Revision ID: 002
Revises: 001
Create Date: 2026-04-14
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL for the vector column — same pattern as vector columns in 001.
    op.execute("""
        CREATE TABLE slack_message_embedding (
            id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
            workspace_id UUID        NOT NULL REFERENCES workspace(id),
            channel_id   TEXT        NOT NULL,
            message_ts   TEXT        NOT NULL,
            author_id    TEXT        NOT NULL,
            text         TEXT        NOT NULL,
            embedding    vector(1536) NOT NULL,
            stored_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Dedup: same message arriving in two overlapping scan windows is silently skipped.
    op.execute("""
        CREATE UNIQUE INDEX uq_slack_msg_embedding_ts
        ON slack_message_embedding (workspace_id, channel_id, message_ts)
    """)

    op.execute("""
        CREATE INDEX ix_slack_msg_embedding_workspace
        ON slack_message_embedding (workspace_id)
    """)

    # Enables efficient range delete for the 30-day TTL cleanup task.
    op.execute("""
        CREATE INDEX ix_slack_msg_embedding_stored_at
        ON slack_message_embedding (stored_at)
    """)

    # IVFFlat for cosine similarity search.
    # lists=10 is appropriate for <100k rows per workspace at pilot scale.
    # Upgrade to HNSW when any workspace exceeds ~100k rows.
    op.execute("""
        CREATE INDEX ix_slack_msg_embedding_ivfflat
        ON slack_message_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS slack_message_embedding")
