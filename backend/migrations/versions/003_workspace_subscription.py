"""Add subscription_status and trial_ends_at to workspace

Revision ID: 003
Revises: 002
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace",
        sa.Column(
            "subscription_status",
            sa.String(16),
            nullable=False,
            server_default="trialing",
        ),
    )
    op.add_column(
        "workspace",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill: existing workspaces get a 30-day trial from their creation date
    op.execute(
        "UPDATE workspace SET trial_ends_at = created_at + INTERVAL '30 days'"
    )


def downgrade() -> None:
    op.drop_column("workspace", "trial_ends_at")
    op.drop_column("workspace", "subscription_status")
