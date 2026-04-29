"""add stripe billing columns to workspace

Revision ID: 006
Revises: 005
Create Date: 2026-04-29
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace", sa.Column("stripe_customer_id", sa.String(64), nullable=True))
    op.add_column("workspace", sa.Column("stripe_subscription_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("workspace", "stripe_subscription_id")
    op.drop_column("workspace", "stripe_customer_id")