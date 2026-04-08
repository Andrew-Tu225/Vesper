"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

# Tables that carry an updated_at column and need a DB-level trigger.
# The trigger fires on every UPDATE, so updated_at stays correct even
# for bulk updates issued via session.execute() that bypass ORM unit-of-work.
_UPDATED_AT_TABLES = [
    "users",
    "workspace",
    "oauth_token",
    "raw_event",
    "content_signal",
    "draft_post",
]


def upgrade() -> None:
    # ── Extensions ─────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── updated_at trigger function ────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("google_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])

    # ── workspace ──────────────────────────────────────────────────────────────
    op.create_table(
        "workspace",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("slack_team_id", sa.String(64), nullable=True),
        sa.Column("linkedin_org_id", sa.String(64), nullable=True),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("onboarding_step", sa.String(32), server_default="connect_slack", nullable=False),
        sa.Column("onboarding_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_workspace_slack_team_id", "workspace", ["slack_team_id"])
    op.create_unique_constraint("uq_workspace_linkedin_org_id", "workspace", ["linkedin_org_id"])

    # ── workspace_member ───────────────────────────────────────────────────────
    op.create_table(
        "workspace_member",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspace.id"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(32), server_default="member", nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workspace_member_user_id", "workspace_member", ["user_id"])

    # ── oauth_token ────────────────────────────────────────────────────────────
    op.create_table(
        "oauth_token",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("token_type", sa.String(32), nullable=False),
        sa.Column("encrypted_token", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("tag", sa.LargeBinary(), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Nonce must be unique: AES-GCM security breaks on nonce reuse under the same key.
    # The DB constraint converts a probabilistic cryptographic property into a hard guarantee.
    op.create_unique_constraint("uq_oauth_token_nonce", "oauth_token", ["nonce"])
    # Partial unique indexes enforce one token per (workspace/user, provider, type)
    op.execute(
        "CREATE UNIQUE INDEX uq_oauth_token_workspace_level "
        "ON oauth_token (workspace_id, provider, token_type) "
        "WHERE user_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_oauth_token_user_level "
        "ON oauth_token (workspace_id, user_id, provider, token_type) "
        "WHERE user_id IS NOT NULL"
    )

    # ── raw_event ──────────────────────────────────────────────────────────────
    op.create_table(
        "raw_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("source_channel", sa.String(255), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("classification", postgresql.JSONB(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_raw_event_dedup "
        "ON raw_event (workspace_id, source_type, source_id) "
        "WHERE status != 'error'"
    )
    op.create_index("ix_raw_event_status_created", "raw_event", ["status", "created_at"])

    # ── content_signal ─────────────────────────────────────────────────────────
    op.create_table(
        "content_signal",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("raw_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("raw_event.id"), nullable=False, unique=True),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("signal_type", sa.String(32), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("redacted_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("sensitivity", sa.String(16), server_default="unknown", nullable=False),
        sa.Column("status", sa.String(32), server_default="detected", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_content_signal_workspace_status", "content_signal", ["workspace_id", "status"])
    op.create_index("ix_content_signal_created_at", "content_signal", ["created_at"])

    # ── draft_post ─────────────────────────────────────────────────────────────
    op.create_table(
        "draft_post",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("content_signal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_signal.id"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("variant_number", sa.SmallInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("slack_message_ts", sa.String(64), nullable=True),
        sa.Column("slack_channel_id", sa.String(64), nullable=True),
        sa.Column("publish_target", sa.String(32), nullable=True),
        sa.Column("publisher_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linkedin_post_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_draft_post_scheduled "
        "ON draft_post (scheduled_at) "
        "WHERE is_selected = TRUE AND published_at IS NULL"
    )

    # ── style_entry ────────────────────────────────────────────────────────────
    # Use raw DDL so the embedding column gets the native vector(1536) type,
    # which SQLAlchemy's create_table cannot render without the extension loaded first.
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

    # ── audit_log ──────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("actor", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_workspace_created", "audit_log", ["workspace_id", "created_at"])

    # ── updated_at triggers (one per table with that column) ──────────────────
    for table in _UPDATED_AT_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """)


def downgrade() -> None:
    # Drop triggers before tables
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at")

    op.drop_table("audit_log")
    op.drop_table("style_entry")
    op.drop_table("draft_post")
    op.drop_table("content_signal")
    op.drop_table("raw_event")
    op.drop_table("oauth_token")
    op.drop_table("workspace_member")
    op.drop_table("workspace")
    op.drop_table("users")
    # Extensions are shared infrastructure — do not drop them here.
    # To remove them, do so manually after confirming no other objects depend on them.
