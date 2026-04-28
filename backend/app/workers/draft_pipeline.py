"""
draft_pipeline queue — classify -> enrich_context -> generate_draft

Each task takes a signal_id (str UUID), does its work, and returns signal_id so that
Celery's native chain primitive can pass it to the next step automatically.

Use `run_draft_pipeline(signal_id)` as the single entry point — it builds and dispatches
the full chain. Never dispatch individual tasks in isolation.

Pipeline steps
--------------
classify_signal
    No LLM call. Reconstructs original_text from raw_payload['messages'] (set by the
    intake scanner). signal_type and summary were already written by batch_classify.
    Status -> classified.

enrich_context
    GPT-4o-mini agent loop (max 5 iterations, see services/drafter.py). Two tools:
      get_slack_thread -- fetch full Slack thread replies
      search_context   -- pgvector cosine search over slack_message_embedding (30-day window)
    Writes context_summary to metadata_['enrichment']. Status -> enriched.

generate_draft
    GPT-4o generates draft_variant_count LinkedIn post variants using summary,
    context_summary, and raw source messages. Inserts DraftPost rows (idempotent via
    ON CONFLICT), posts Block Kit approval card to social_queue_channel, stores
    slack_message_ts on each DraftPost. Status -> in_review.
"""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID, uuid4

from celery import chain

from app.db_sync import get_sync_pool
from app.services.drafter import run_enrich_agent, run_generate, run_rewrite
from app.workers.celery_app import celery_app
from app.workers.constants import Queue, SignalStatus

logger = logging.getLogger(__name__)

__all__ = [
    "run_draft_pipeline",
    "classify_signal",
    "enrich_context",
    "generate_draft",
    "rewrite_draft",
]


# ---------------------------------------------------------------------------
# Private sync DB helpers
# ---------------------------------------------------------------------------

def _load_signal_row(signal_id: str) -> dict | None:
    """Load all ContentSignal columns needed by the pipeline steps."""
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, workspace_id, signal_type, summary, original_text,
                       redacted_text, raw_payload, metadata, source_channel, source_id
                FROM content_signal
                WHERE id = %s::uuid
                """,
                (signal_id,),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if row is None:
        return None
    return {
        "id": str(row[0]),
        "workspace_id": str(row[1]),
        "signal_type": row[2],
        "summary": row[3],
        "original_text": row[4],
        "redacted_text": row[5],
        "raw_payload": row[6] or {},
        "metadata_": row[7] or {},
        "source_channel": row[8],
        "source_id": row[9],
    }


def _load_workspace_settings(workspace_id: str) -> dict:
    """Return workspace.settings JSONB as a plain dict. Returns {} on failure."""
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT settings FROM workspace WHERE id = %s::uuid",
                (workspace_id,),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    return row[0] if row and row[0] else {}


def _update_signal_status(signal_id: str, status: SignalStatus) -> None:
    """Update ContentSignal.status. Raises psycopg2.Error on failure."""
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


def _search_similar_messages(
    workspace_id: str,
    query_vec: list[float],
    limit: int = 5,
) -> list[dict]:
    """pgvector cosine similarity search over slack_message_embedding (30-day window).

    Used as the search_fn injected into run_enrich_agent.
    """
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT text, message_ts, channel_id,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM slack_message_embedding
                WHERE workspace_id = %s::uuid
                  AND stored_at > now() - INTERVAL '30 days'
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vec_str, workspace_id, vec_str, limit),
            )
            rows = cur.fetchall()
    finally:
        pool.putconn(conn)

    return [
        {
            "text": r[0],
            "message_ts": r[1],
            "channel_id": r[2],
            "similarity": float(r[3]),
        }
        for r in rows
    ]


def _insert_draft_posts(
    signal_id: str,
    workspace_id: str,
    variants: list[str],
) -> list[str]:
    """Insert DraftPost rows, one per variant. Returns the actual post UUIDs.

    ON CONFLICT DO UPDATE makes this idempotent: a Celery retry overwrites
    the body instead of creating duplicates.
    """
    post_ids: list[str] = []
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            for i, body in enumerate(variants, start=1):
                post_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO draft_post
                        (id, content_signal_id, workspace_id, variant_number, body)
                    VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s)
                    ON CONFLICT (content_signal_id, variant_number)
                    DO UPDATE SET body = EXCLUDED.body
                    RETURNING id
                    """,
                    (post_id, signal_id, workspace_id, i, body),
                )
                returned = cur.fetchone()
                post_ids.append(str(returned[0]) if returned else post_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)

    return post_ids


def _update_draft_posts_slack_ts(
    post_ids: list[str],
    message_ts: str,
    channel_id: str,
) -> None:
    """Store the Slack card message_ts on every DraftPost row for the signal."""
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            for post_id in post_ids:
                cur.execute(
                    """
                    UPDATE draft_post
                    SET slack_message_ts = %s, slack_channel_id = %s
                    WHERE id = %s::uuid
                    """,
                    (message_ts, channel_id, post_id),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def _build_approval_card(
    summary: str,
    variants: list[str],
    signal_id: str,
) -> list[dict]:
    """Build the Slack Block Kit approval card for a drafted signal.

    Layout: header -> (variant text + Approve / Rewrite buttons) x N -> Reject button.
    Each button value encodes {"signal_id": ..., "variant_number": N}.
    """
    blocks: list[dict] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*New content signal*\n{summary[:280]}",
            },
        },
        {"type": "divider"},
    ]

    for i, body in enumerate(variants, start=1):
        button_value = json.dumps({"signal_id": signal_id, "variant_number": i})

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Variant {i}*\n{body}"},
        })
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve & Schedule"},
                    "style": "primary",
                    "action_id": "approve_signal",
                    "value": button_value,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Rewrite"},
                    "action_id": "rewrite_signal",
                    "value": button_value,
                },
            ],
        })
        if i < len(variants):
            blocks.append({"type": "divider"})

    blocks.extend([
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "action_id": "reject_signal",
                    "value": json.dumps({"signal_id": signal_id, "variant_number": 1}),
                },
            ],
        },
    ])

    return blocks


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
        logger.error("run_draft_pipeline: invalid UUID %r -- aborting", signal_id)
        return

    pipeline = chain(
        classify_signal.s(signal_id),
        enrich_context.s(),
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
    """Reconstruct original_text from raw_payload; status -> classified.

    signal_type and summary were already set by batch_classify during intake.
    No LLM call is needed here — this step materialises original_text for
    the downstream redaction and generation steps.
    """
    logger.info("classify_signal: signal_id=%s", signal_id)

    try:
        UUID(signal_id)
    except ValueError:
        logger.error("classify_signal: invalid UUID %r -- dropping", signal_id)
        return signal_id

    row = _load_signal_row(signal_id)
    if row is None:
        logger.error("classify_signal: signal %s not found -- dropping", signal_id)
        return signal_id

    messages = row["raw_payload"].get("messages", [])
    original_text = "\n\n".join(
        m["text"] for m in messages if m.get("text", "").strip()
    )

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE content_signal
                SET original_text = %s, status = %s
                WHERE id = %s::uuid
                """,
                (original_text or None, str(SignalStatus.CLASSIFIED), signal_id),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.exception("classify_signal: DB update failed for %s", signal_id)
        raise self.retry(exc=exc)
    finally:
        pool.putconn(conn)

    return signal_id


@celery_app.task(
    name="app.workers.draft_pipeline.enrich_context",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def enrich_context(self, signal_id: str) -> str:
    """Run the enrichment agent loop; write context_summary -> metadata_['enrichment'].

    Agent has access to get_slack_thread and search_context tools (see drafter.py).
    Hard cap: 5 iterations. Falls back to signal summary on agent failure.
    Status -> enriched.
    """
    logger.info("enrich_context: signal_id=%s", signal_id)

    row = _load_signal_row(signal_id)
    if row is None:
        logger.error("enrich_context: signal %s not found -- dropping", signal_id)
        return signal_id

    # Pass full (ts, channel_id, text) triples so the agent has the source message
    # text upfront without needing a tool call, and has the correct channel_id for
    # each ts when it does call get_slack_thread.
    # A signal can span multiple channels since all enrichment_channels are batched
    # together for classification, so source_channel alone is not sufficient.
    raw_messages: list[dict] = row["raw_payload"].get("messages", [])
    source_messages = [
        {"ts": m["ts"], "channel_id": m["channel_id"], "text": m.get("text", "")}
        for m in raw_messages
        if m.get("ts") and m.get("channel_id")
    ]
    if not source_messages and row["source_id"]:
        source_messages = [{
            "ts": row["source_id"],
            "channel_id": row["source_channel"] or "",
            "text": row["original_text"] or "",
        }]

    try:
        context_summary, iterations = asyncio.run(run_enrich_agent(
            workspace_id=row["workspace_id"],
            summary=row["summary"] or "",
            signal_type=row["signal_type"] or "unknown",
            source_messages=source_messages,
            search_fn=_search_similar_messages,
        ))
    except Exception as exc:
        logger.exception("enrich_context: agent failed for %s", signal_id)
        raise self.retry(exc=exc)

    logger.info(
        "enrich_context: signal=%s iterations=%d context_len=%d",
        signal_id, iterations, len(context_summary),
    )

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            enrichment = json.dumps({
                "context_summary": context_summary,
                "iterations": iterations,
            })
            cur.execute(
                """
                UPDATE content_signal
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{enrichment}',
                    %s::jsonb
                ),
                status = %s
                WHERE id = %s::uuid
                """,
                (enrichment, str(SignalStatus.ENRICHED), signal_id),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.exception("enrich_context: DB update failed for %s", signal_id)
        raise self.retry(exc=exc)
    finally:
        pool.putconn(conn)

    return signal_id


@celery_app.task(
    name="app.workers.draft_pipeline.generate_draft",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_draft(self, signal_id: str) -> str:
    """Generate LinkedIn post variants and post the Slack approval card.

    Steps:
    1. Load signal row and workspace settings (social_queue_channel, draft_variant_count).
    2. Call GPT-4o zero-shot to generate draft_variant_count variants.
    3. Insert DraftPost rows (idempotent via ON CONFLICT DO UPDATE on retry).
    4. Post Block Kit approval card to social_queue_channel.
    5. Store slack_message_ts + slack_channel_id on each DraftPost.
    6. Status -> in_review.
    """
    logger.info("generate_draft: signal_id=%s", signal_id)

    from app.services.slack_client import SlackClientError, get_workspace_client, post_message

    row = _load_signal_row(signal_id)
    if row is None:
        logger.error("generate_draft: signal %s not found -- dropping", signal_id)
        return signal_id

    workspace_id = row["workspace_id"]
    ws_settings = _load_workspace_settings(workspace_id)
    variant_count = int(ws_settings.get("draft_variant_count", 2))
    social_queue_channel = str(ws_settings.get("social_queue_channel", "vesper-ai"))

    context_summary = (row["metadata_"].get("enrichment") or {}).get("context_summary", "")

    raw_messages: list[dict] = row["raw_payload"].get("messages", [])
    source_messages = [
        {"ts": m["ts"], "channel_id": m["channel_id"], "text": m.get("text", "")}
        for m in raw_messages
        if m.get("ts") and m.get("channel_id") and m.get("text", "").strip()
    ]

    try:
        variants = asyncio.run(run_generate(
            summary=row["summary"] or "",
            signal_type=row["signal_type"] or "unknown",
            context_summary=context_summary,
            variant_count=variant_count,
            source_messages=source_messages or None,
        ))
    except Exception as exc:
        logger.exception("generate_draft: LLM failed for %s", signal_id)
        raise self.retry(exc=exc)

    try:
        post_ids = _insert_draft_posts(signal_id, workspace_id, variants)
    except Exception as exc:
        logger.exception("generate_draft: DraftPost insert failed for %s", signal_id)
        raise self.retry(exc=exc)

    try:
        slack_client = get_workspace_client(workspace_id)
        blocks = _build_approval_card(row["summary"] or "", variants, signal_id)
        fallback_text = f"New content signal: {(row['summary'] or '')[:100]}"
        message_ts = post_message(slack_client, social_queue_channel, blocks, fallback_text)
    except SlackClientError as exc:
        logger.exception("generate_draft: Slack post failed for %s", signal_id)
        raise self.retry(exc=exc)

    try:
        _update_draft_posts_slack_ts(post_ids, message_ts, social_queue_channel)
        _update_signal_status(signal_id, SignalStatus.IN_REVIEW)
    except Exception as exc:
        logger.exception("generate_draft: post-Slack DB update failed for %s", signal_id)
        raise self.retry(exc=exc)

    logger.info(
        "generate_draft: signal=%s %d variants posted -> in_review (ts=%s)",
        signal_id, len(variants), message_ts,
    )
    return signal_id


# ---------------------------------------------------------------------------
# Rewrite helpers
# ---------------------------------------------------------------------------

def _build_rewrite_card(
    summary: str,
    body: str,
    signal_id: str,
    variant_number: int,
) -> list[dict]:
    """Build a single-variant Slack card for a rewritten draft.

    Shows only the revised variant so the reviewer evaluates it in isolation,
    without being distracted by the original variants that are no longer relevant.
    """
    button_value = json.dumps({"signal_id": signal_id, "variant_number": variant_number})
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Rewritten draft*\n{summary[:280]}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": body},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve & Schedule"},
                    "style": "primary",
                    "action_id": "approve_signal",
                    "value": button_value,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Rewrite"},
                    "action_id": "rewrite_signal",
                    "value": button_value,
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "action_id": "reject_signal",
                    "value": button_value,
                },
            ],
        },
    ]


def _load_draft_post(signal_id: str, variant_number: int) -> dict | None:
    """Load a single DraftPost row by signal + variant. Returns None if not found."""
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, body, feedback
                FROM draft_post
                WHERE content_signal_id = %s::uuid
                  AND variant_number = %s
                """,
                (signal_id, variant_number),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if row is None:
        return None
    return {"id": str(row[0]), "body": row[1], "feedback": row[2]}


def _load_slack_card_coords(signal_id: str) -> tuple[str, str] | None:
    """Return (slack_message_ts, slack_channel_id) for the existing approval card.

    Finds the first DraftPost row for this signal that has both fields set.
    Returns None if the card was never posted (shouldn't happen in normal flow).
    """
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT slack_message_ts, slack_channel_id
                FROM draft_post
                WHERE content_signal_id = %s::uuid
                  AND slack_message_ts IS NOT NULL
                  AND slack_channel_id IS NOT NULL
                LIMIT 1
                """,
                (signal_id,),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if row is None:
        return None
    return row[0], row[1]


def _update_draft_post_body(signal_id: str, variant_number: int, new_body: str) -> None:
    """Overwrite DraftPost.body for a specific variant."""
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE draft_post
                SET body = %s
                WHERE content_signal_id = %s::uuid
                  AND variant_number = %s
                """,
                (new_body, signal_id, variant_number),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@celery_app.task(
    name="app.workers.draft_pipeline.rewrite_draft",
    queue=Queue.DRAFT_PIPELINE,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def rewrite_draft(self, signal_id: str, variant_number: int) -> str:
    """Revise a single draft variant using reviewer feedback and signal context.

    Unlike generate_draft, this edits one specific variant in-place rather
    than regenerating all variants from scratch. After updating the body, the
    existing Slack approval card is updated in-place so the reviewer sees the
    revised content with fresh action buttons on the same message.

    Steps:
    1. Load signal row and workspace settings.
    2. Load the target DraftPost (has .feedback set by handle_rewrite).
    3. Call GPT-4o run_rewrite with existing body + feedback + signal context.
    4. Update DraftPost.body for the target variant.
    5. Update the existing Slack card in-place via chat.update.
    6. Status -> in_review (reset so card actions are active again).
    """
    logger.info("rewrite_draft: signal_id=%s variant=%s", signal_id, variant_number)

    from app.services.slack_client import SlackClientError, get_workspace_client, update_message

    row = _load_signal_row(signal_id)
    if row is None:
        logger.error("rewrite_draft: signal %s not found -- dropping", signal_id)
        return signal_id

    draft = _load_draft_post(signal_id, variant_number)
    if draft is None:
        logger.error(
            "rewrite_draft: DraftPost not found for signal=%s variant=%s -- dropping",
            signal_id, variant_number,
        )
        return signal_id

    workspace_id = row["workspace_id"]
    context_summary = (row["metadata_"].get("enrichment") or {}).get("context_summary")
    raw_messages: list[dict] = row["raw_payload"].get("messages", [])
    source_messages = [
        {"ts": m["ts"], "channel_id": m["channel_id"], "text": m.get("text", "")}
        for m in raw_messages
        if m.get("ts") and m.get("channel_id") and m.get("text", "").strip()
    ]

    try:
        revised_body = asyncio.run(run_rewrite(
            existing_body=draft["body"],
            feedback=draft["feedback"] or "",
            summary=row["summary"] or "",
            context_summary=context_summary,
            source_messages=source_messages or None,
        ))
    except Exception as exc:
        logger.exception("rewrite_draft: LLM failed for signal=%s variant=%s", signal_id, variant_number)
        raise self.retry(exc=exc)

    try:
        _update_draft_post_body(signal_id, variant_number, revised_body)
    except Exception as exc:
        logger.exception("rewrite_draft: body update failed for signal=%s", signal_id)
        raise self.retry(exc=exc)

    coords = _load_slack_card_coords(signal_id)
    if coords is None:
        logger.warning(
            "rewrite_draft: no card coords found for signal=%s — skipping Slack update",
            signal_id,
        )
    else:
        card_ts, card_channel = coords
        try:
            slack_client = get_workspace_client(workspace_id)
            blocks = _build_rewrite_card(
                row["summary"] or "", revised_body, signal_id, variant_number
            )
            update_message(slack_client, card_channel, card_ts, blocks)
        except SlackClientError as exc:
            logger.exception("rewrite_draft: Slack update failed for signal=%s", signal_id)
            raise self.retry(exc=exc)

    try:
        _update_signal_status(signal_id, SignalStatus.IN_REVIEW)
    except Exception as exc:
        logger.exception("rewrite_draft: status update failed for signal=%s", signal_id)
        raise self.retry(exc=exc)

    logger.info(
        "rewrite_draft: signal=%s variant=%s rewritten -> in_review (card updated in-place)",
        signal_id, variant_number,
    )
    return signal_id
