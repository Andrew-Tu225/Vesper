"""
draft_pipeline queue — classify → enrich_context → redact → generate

Each task takes a signal_id (str UUID), does its work, and returns signal_id so that
Celery's native chain primitive can pass it to the next step automatically.

Use `run_draft_pipeline(signal_id)` as the single entry point — it builds and dispatches
the full chain. Never dispatch individual tasks in isolation.

Phase 1.4 scope
---------------
- run_draft_pipeline : entry point — builds the Celery chain and dispatches it
- classify_signal    : stub — updates status → classified
- enrich_context     : stub — updates status → enriched
- redact_signal      : stub — placeholder for Phase 2
- generate_draft     : stub — placeholder for Phase 2

Full LLM implementations are deferred to Phase 2.
"""

import logging
from uuid import UUID

from celery import chain

from app.db_sync import get_sync_pool
from app.workers.celery_app import celery_app
from app.workers.constants import Queue, SignalStatus

logger = logging.getLogger(__name__)

__all__ = ["run_draft_pipeline", "classify_signal", "enrich_context", "redact_signal", "generate_draft"]


def _update_signal_status(signal_id: str, status: SignalStatus) -> None:
    """Update ContentSignal.status using a pooled sync psycopg2 connection.

    Raises psycopg2.Error on failure — callers should catch and retry.
    """
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE content_signal SET status = %s WHERE id = %s::uuid",
                (str(status), signal_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_draft_pipeline(signal_id: str) -> None:
    """Build and dispatch the full draft pipeline chain for a single signal.

    This is the only correct way to start the pipeline. Dispatching individual
    tasks in isolation breaks retry semantics and can cause duplicate downstream runs.
    """
    try:
        UUID(signal_id)
    except ValueError:
        logger.error("run_draft_pipeline: invalid UUID %r — aborting", signal_id)
        return

    pipeline = chain(
        classify_signal.s(signal_id),
        enrich_context.s(),
        redact_signal.s(),
        generate_draft.s(),
    )
    pipeline.apply_async()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.draft_pipeline.classify_signal",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def classify_signal(self, signal_id: str) -> str:
    """Classify a raw content signal as content-worthy or noise.

    Phase 2 will call GPT-4o-mini to:
    - Determine if the signal is worth drafting
    - Set signal_type (customer_praise, product_win, etc.)
    - Reject noise signals early

    Returns signal_id for the next step in the chain.
    """
    logger.info("classify_signal: signal_id=%s (stub)", signal_id)

    try:
        UUID(signal_id)
    except ValueError:
        logger.error("classify_signal: invalid UUID %r — dropping", signal_id)
        return signal_id

    try:
        _update_signal_status(signal_id, SignalStatus.CLASSIFIED)
    except Exception as exc:
        logger.exception("classify_signal: DB update failed for %s", signal_id)
        raise self.retry(exc=exc)

    return signal_id


@celery_app.task(
    name="app.workers.draft_pipeline.enrich_context",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def enrich_context(self, signal_id: str) -> str:
    """Agentic context-enrichment step.

    Phase 2 will run a GPT-4o-mini agent with tool use that:
    1. Reads the classified signal + summary
    2. Decides what context is still needed
    3. Calls retrieval tools (up to 5 iterations):

       Slack signals: get_slack_thread, get_slack_channel_history, search_slack_messages
       Email signals: get_email_thread (full Re: chain), search_emails_by_sender,
                      search_emails — all via live Gmail API using the workspace OAuth token

    4. Self-judges whether context is sufficient; loops if not (max 5 iterations)
    5. Produces a context_summary stored in content_signal.metadata_['enrichment']

    For now (Phase 1.4): no-op stub — sets status → enriched.

    Returns signal_id for the next step in the chain.
    """
    logger.info("enrich_context: signal_id=%s (stub)", signal_id)

    try:
        UUID(signal_id)
    except ValueError:
        logger.error("enrich_context: invalid UUID %r — dropping", signal_id)
        return signal_id

    try:
        _update_signal_status(signal_id, SignalStatus.ENRICHED)
    except Exception as exc:
        logger.exception("enrich_context: DB update failed for %s", signal_id)
        raise self.retry(exc=exc)

    return signal_id


@celery_app.task(
    name="app.workers.draft_pipeline.redact_signal",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def redact_signal(self, signal_id: str) -> str:
    """Remove sensitive details before the signal reaches the drafter.

    Phase 2 will call GPT-4o-mini to redact PII, customer names, and
    other sensitive content flagged by the sensitivity field.
    Populates redacted_text and updates sensitivity.

    Returns signal_id for the next step in the chain.
    """
    logger.info("redact_signal: signal_id=%s (stub)", signal_id)
    # Phase 2: implement redaction, update redacted_text + sensitivity
    return signal_id


@celery_app.task(
    name="app.workers.draft_pipeline.generate_draft",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_draft(self, signal_id: str) -> str:
    """Generate LinkedIn post variants using the style library as few-shot examples.

    Phase 2 will:
    - Retrieve top 2–3 style-library entries via pgvector cosine similarity
    - Call GPT-4o to generate draft_variant_count variants
    - Create DraftPost records and set status → drafted
    - Post approval card to Slack #vesper-ai

    Returns signal_id.
    """
    logger.info("generate_draft: signal_id=%s (stub)", signal_id)
    # Phase 2: implement generation pipeline
    return signal_id
