"""Add provider_user_id to oauth_token

Stores the provider-side user identifier (e.g. LinkedIn sub / person ID)
so the publishing worker can build the author URN without a separate API call.

Revision ID: 007
Revises: 006
Create Date: 2026-05-04
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "oauth_token",
        sa.Column("provider_user_id", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oauth_token", "provider_user_id")