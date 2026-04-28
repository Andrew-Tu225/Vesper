"""
Pydantic schemas for LLM-facing structured outputs and inter-service data transfer.

All schemas used across services (classifier, draft pipeline, enrichment) live here
so imports are predictable and openai_client.py stays a thin factory.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Intake / batch classification
# ---------------------------------------------------------------------------

class SlackMessage(BaseModel):
    """A single Slack message from the channel scan window.

    The batch classifier receives a flat chronological list of these.
    A content signal can emerge from multiple related messages (a thread,
    a back-and-forth), so the LLM groups clusters itself rather than
    treating each message as an independent unit.
    """

    source_id: str = Field(description="message_ts — unique Slack identifier for this message")
    channel_id: str
    user_id: str
    text: str
    thread_ts: str | None = Field(
        default=None,
        description="Set on thread replies; groups messages belonging to the same thread",
    )
    reaction_count: int = Field(
        default=0,
        description="Total emoji reactions on this message — a proxy for team importance",
    )


class ContentSignalCandidate(BaseModel):
    """A content signal identified by the batch classifier.

    Only worthy signals are returned — noise is excluded entirely.
    A signal can span multiple source messages (e.g. a full thread, a follow-up exchange).
    """

    source_ids: list[str] = Field(
        description=(
            "All message_ts values that form this signal. "
            "source_ids[0] is the dedup anchor and maps to ContentSignal.source_id in the DB."
        )
    )
    signal_type: str = Field(
        description=(
            "One of: customer_praise, product_win, launch_update, hiring, founder_insight"
        )
    )
    summary: str = Field(
        description=(
            "1–2 sentence summary of the signal, written as a brief for a copywriter. "
            "Stored on ContentSignal.summary and used as context for draft generation."
        )
    )
    reason: str = Field(description="Why this is post-worthy (written to logs; not persisted)")


class BatchClassifyResponse(BaseModel):
    """Structured output envelope for the batch classification LLM call.

    candidates         — worthy content signals identified from the message batch.
    embed_message_ids  — source_ids (Slack message_ts values) the LLM flagged as
                         carrying enough semantic content to store for future context
                         retrieval. These are IDs only; the intake worker looks up
                         the full message text from its local msg_lookup dict, embeds
                         the text, and stores the vector in slack_message_cache.
    """

    candidates: list[ContentSignalCandidate]
    embed_message_ids: list[str] = []


# ---------------------------------------------------------------------------
# Draft pipeline — generation
# ---------------------------------------------------------------------------

class GenerateDraftResponse(BaseModel):
    """Structured output for LinkedIn draft generation."""

    variants: list[str] = Field(
        description=(
            "One LinkedIn post body per requested variant. "
            "Each variant takes a different angle on the same signal "
            "(e.g. result-led, journey-led)."
        )
    )
