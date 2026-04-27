"""
Pydantic schema for Workspace.settings JSONB.

Usage
-----
Parse and validate:
    ws_settings = WorkspaceSettings.model_validate(workspace.settings)

Write back (merge):
    workspace.settings = {
        **workspace.settings,
        **ws_settings.model_dump(exclude_unset=True),
    }
"""

import datetime

from pydantic import BaseModel, Field, field_validator


class WorkspaceSettings(BaseModel):
    """Typed view of the Workspace.settings JSONB column.

    All fields are optional so partial settings documents are accepted
    without raising validation errors.
    """

    # ------------------------------------------------------------------
    # Intake scanner settings
    # ------------------------------------------------------------------

    # Slack channel IDs the batch scanner and enrichment agent are allowed to read.
    # e.g. ["C01ABC123", "C02DEF456"]
    enrichment_channels: list[str] = Field(default_factory=list)

    # Gmail label names to scan for content signals.
    # e.g. ["INBOX", "Label_1"]
    gmail_labels: list[str] = Field(default_factory=list)

    # How many times per day the intake scanner runs (Celery Beat interval).
    # e.g. 3 → every 8 hours.
    intake_runs_per_day: int = 3

    # Scan checkpoints — updated by each intake task after a successful run.
    # Stored as ISO-8601 UTC strings; None means "scan from scratch".
    last_slack_scanned_at: datetime.datetime | None = None
    last_gmail_scanned_at: datetime.datetime | None = None

    @field_validator("last_slack_scanned_at", "last_gmail_scanned_at", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: object) -> object:
        """Attach UTC timezone to naive datetimes read back from JSONB.

        PostgreSQL JSONB stores datetimes as plain strings. If a naive datetime
        slips in (e.g. from datetime.utcnow() or a raw SQL now()), comparing it
        against an aware datetime raises TypeError. This validator normalises all
        incoming values to UTC-aware.
        """
        if isinstance(v, datetime.datetime) and v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v

    # ------------------------------------------------------------------
    # Draft pipeline settings
    # ------------------------------------------------------------------

    # Slack channel where approval cards are posted (default: #vesper-ai)
    social_queue_channel: str = "vesper-ai"

    # Maximum number of draft variants to generate per signal
    draft_variant_count: int = 3

    model_config = {"extra": "allow"}  # forward-compatible: unknown keys are preserved
