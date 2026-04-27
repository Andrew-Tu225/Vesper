"""drop style_entry table

style_entry (brand-voice style library) is out of MVP scope.
generate_draft uses zero-shot GPT-4o for the MVP.

Revision ID: 005
Revises: 004
Create Date: 2026-04-27
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_style_entry_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_style_entry_workspace_id")
    op.drop_table("style_entry")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE style_entry (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workspace_id UUID NOT NULL REFERENCES workspace(id),
            draft_post_id UUID REFERENCES draft_post(id),
            content TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            is_seed BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index("ix_style_entry_workspace_id", "style_entry", ["workspace_id"])
    op.execute(
        "CREATE INDEX ix_style_entry_embedding_ivfflat "
        "ON style_entry USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 10)"
    )
