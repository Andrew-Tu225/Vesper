"""
Constants for the Vesper worker pipeline.
"""

from enum import StrEnum


class SignalStatus(StrEnum):
    # detected   – raw signal ingested, not yet evaluated
    # classified – LLM confirmed content-worthy; signal_type set
    # enriched   – context-enrichment agent finished; context_summary ready
    # drafted    – one or more DraftPost records created
    # in_review  – approval card sent to Slack #vesper-ai
    # approved   – reviewer accepted a draft variant
    # scheduled  – post queued for a future datetime
    # posted     – successfully published to LinkedIn
    # failed     – terminal failure; will not be retried automatically
    DETECTED = "detected"
    CLASSIFIED = "classified"
    ENRICHED = "enriched"
    DRAFTED = "drafted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"


class SignalType(StrEnum):
    CUSTOMER_PRAISE = "customer_praise"
    PRODUCT_WIN = "product_win"
    LAUNCH_UPDATE = "launch_update"
    HIRING = "hiring"
    FOUNDER_INSIGHT = "founder_insight"


class Sensitivity(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Queue(StrEnum):
    DRAFT_PIPELINE = "draft_pipeline"   # classify → enrich_context → redact → generate
    INTAKE = "intake"                   # scheduled batch scans: Slack channels + Gmail inbox (2–3x/day)
    PUBLISHING = "publishing"           # LinkedIn post delivery
    MAINTENANCE = "maintenance"         # token refresh (Celery Beat), cleanup
