"""remove billing paywall columns

Revision ID: 008
Revises: 007
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("workspace", "stripe_subscription_id")
    op.drop_column("workspace", "stripe_customer_id")
    op.drop_column("workspace", "trial_ends_at")
    op.drop_column("workspace", "subscription_status")


def downgrade() -> None:
    op.add_column(
        "workspace",
        sa.Column("subscription_status", sa.String(16), nullable=False, server_default="active"),
    )
    op.add_column("workspace", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workspace", sa.Column("stripe_customer_id", sa.String(64), nullable=True))
    op.add_column("workspace", sa.Column("stripe_subscription_id", sa.String(64), nullable=True))
