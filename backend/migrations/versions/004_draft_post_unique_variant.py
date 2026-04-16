"""Add unique constraint to draft_post(content_signal_id, variant_number)

Enables ON CONFLICT DO UPDATE in generate_draft so Celery retries overwrite
existing draft rows rather than creating duplicates.

Revision ID: 004
Revises: 003
Create Date: 2026-04-15
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_draft_post_signal_variant",
        "draft_post",
        ["content_signal_id", "variant_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_draft_post_signal_variant", "draft_post", type_="unique")
