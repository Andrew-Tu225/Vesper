"""
intake queue — scheduled batch content scanners (Celery Beat, 2x/day).

Why batch, not real-time
------------------------
A single Slack message rarely has enough context to judge content worthiness.
Running a scan on an accumulated window gives the classifier conversational
context — threads, reactions, follow-ups — before deciding what to draft.

Tasks
-----
scan_slack_channels   Fetch messages from workspace.settings.enrichment_channels
                      since last_slack_scanned_at, batch classify, embed flagged
                      messages, create ContentSignals, dispatch draft pipeline.

scan_gmail_inbox      Phase 3 — not yet implemented.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)

# How far back to scan on the very first run (no last_slack_scanned_at set).
_FIRST_RUN_LOOKBACK_HOURS = 24


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.intake.scan_slack_channels",
    queue=Queue.INTAKE,
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def scan_slack_channels(self, workspace_id: str) -> None:
    """Batch-scan configured Slack channels and create ContentSignals.

    Steps
    -----
    1. Load workspace settings; skip if enrichment_channels is empty.
    2. Fetch messages from each channel since last_slack_scanned_at,
       expanding threads inline.
    3. Batch classify all messages in one LLM call.
    4. Embed messages flagged by the classifier; upsert into
       slack_message_embedding for future enrichment context.
    5. For each candidate: dedup via Redis SETNX, create ContentSignal,
       dispatch run_draft_pipeline.
    6. Update last_slack_scanned_at checkpoint.
    """
    from app.models.workspace_settings import WorkspaceSettings
    from app.services.classifier import ClassifierError, batch_classify
    from app.services.embedder import EmbedderError, embed_texts
    from app.services.schemas import SlackMessage
    from app.services.slack_client import SlackClientError, get_channel_history, get_thread_replies, get_workspace_client

    # ------------------------------------------------------------------
    # 1. Load workspace settings
    # ------------------------------------------------------------------
    row = _load_workspace_row(workspace_id)
    if row is None:
        logger.warning("scan_slack_channels: workspace %s not found or not onboarded — skipping", workspace_id)
        return

    ws_settings = WorkspaceSettings.model_validate(row or {})
    if not ws_settings.enrichment_channels:
        logger.info("scan_slack_channels: workspace %s has no enrichment_channels — skipping", workspace_id)
        return

    # ------------------------------------------------------------------
    # 2. Fetch messages from all channels
    # ------------------------------------------------------------------
    oldest_dt = ws_settings.last_slack_scanned_at
    if oldest_dt is None:
        oldest_dt = datetime.now(tz=timezone.utc) - timedelta(hours=_FIRST_RUN_LOOKBACK_HOURS)
    oldest_ts = oldest_dt.timestamp()

    try:
        client = get_workspace_client(workspace_id)
    except SlackClientError as exc:
        logger.error("scan_slack_channels: cannot get Slack client for %s: %s", workspace_id, exc)
        raise self.retry(exc=exc)

    slack_messages, msg_lookup = _fetch_all_messages(
        client, ws_settings.enrichment_channels, oldest_ts,
        get_channel_history, get_thread_replies,
    )

    if not slack_messages:
        logger.info("scan_slack_channels: no messages since last scan for workspace %s", workspace_id)
        _update_last_scanned(workspace_id)
        return

    logger.info(
        "scan_slack_channels: workspace %s — %d messages across %d channels",
        workspace_id, len(slack_messages), len(ws_settings.enrichment_channels),
    )

    # ------------------------------------------------------------------
    # 3. Batch classify
    # ------------------------------------------------------------------
    try:
        result = asyncio.run(batch_classify(slack_messages))
    except ClassifierError as exc:
        logger.error("scan_slack_channels: classification failed for %s: %s", workspace_id, exc)
        raise self.retry(exc=exc)

    logger.info(
        "scan_slack_channels: workspace %s — %d candidates, %d messages to embed",
        workspace_id, len(result.candidates), len(result.embed_message_ids),
    )

    # ------------------------------------------------------------------
    # 4. Embed flagged messages
    # ------------------------------------------------------------------
    if result.embed_message_ids:
        embed_meta = [
            {
                "ts": ts,
                "channel_id": msg_lookup[ts]["_channel_id"],
                "user_id": msg_lookup[ts].get("user", ""),
                "text": msg_lookup[ts].get("text", "").strip(),
            }
            for ts in result.embed_message_ids
            if ts in msg_lookup and msg_lookup[ts].get("text", "").strip()
        ]
        if embed_meta:
            try:
                embeddings = asyncio.run(embed_texts([m["text"] for m in embed_meta]))
                _upsert_embeddings(workspace_id, embed_meta, embeddings)
            except EmbedderError as exc:
                # Non-fatal — log and continue to signal creation
                logger.error("scan_slack_channels: embedding failed for %s: %s", workspace_id, exc)

    # ------------------------------------------------------------------
    # 5. Dedup + create ContentSignals + dispatch pipeline
    # ------------------------------------------------------------------
    from app.redis_sync import get_sync_redis
    from app.workers.draft_pipeline import run_draft_pipeline

    redis_client = get_sync_redis()
    created = 0

    for candidate in result.candidates:
        anchor = candidate.source_ids[0]
        dedup_key = f"dedup:{workspace_id}:slack:{anchor}"

        acquired = redis_client.set(dedup_key, "1", nx=True, ex=86400)
        if not acquired:
            logger.info("scan_slack_channels: dedup hit %s — skipping", dedup_key)
            continue

        signal_id = _create_content_signal(workspace_id, candidate, msg_lookup)
        if signal_id:
            run_draft_pipeline(signal_id)
            created += 1

    logger.info("scan_slack_channels: workspace %s — created %d ContentSignals", workspace_id, created)

    # ------------------------------------------------------------------
    # 6. Update checkpoint
    # ------------------------------------------------------------------
    _update_last_scanned(workspace_id)


# ---------------------------------------------------------------------------
# Gmail stub (Phase 3)
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.intake.scan_gmail_inbox",
    queue=Queue.INTAKE,
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def scan_gmail_inbox(self, workspace_id: str) -> None:
    """Batch-scan Gmail labels and create ContentSignals for worthy emails.

    Phase 3 implementation.
    """
    logger.info("scan_gmail_inbox: workspace_id=%s (stub)", workspace_id)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_workspace_row(workspace_id: str) -> dict | None:
    """Return workspace.settings dict if the workspace is onboarded, else None."""
    from app.db_sync import get_sync_pool

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT settings FROM workspace
                WHERE id = %s::uuid
                  AND onboarding_complete = TRUE
                """,
                (workspace_id,),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    return row[0] if row else None


def _fetch_all_messages(
    client,
    channels: list[str],
    oldest_ts: float,
    get_channel_history,
    get_thread_replies,
) -> tuple[list, dict]:
    """Fetch messages from all channels, expanding thread replies inline.

    Returns (slack_messages, msg_lookup) where:
      slack_messages — list[SlackMessage] ready for the classifier
      msg_lookup     — {message_ts: raw_dict_with_channel_id} for embedding + signal creation
    """
    from app.services.schemas import SlackMessage
    from app.services.slack_client import SlackClientError

    msg_lookup: dict[str, dict] = {}
    slack_messages: list[SlackMessage] = []

    for channel_id in channels:
        try:
            raw_messages = get_channel_history(client, channel_id, oldest=oldest_ts)
        except SlackClientError as exc:
            logger.warning("scan_slack_channels: cannot fetch channel %s: %s", channel_id, exc)
            continue

        thread_replies: list[dict] = []
        for msg in raw_messages:
            tagged = {**msg, "_channel_id": channel_id}
            msg_lookup[msg["ts"]] = tagged

            if int(msg.get("reply_count", 0)) > 0:
                try:
                    replies = get_thread_replies(client, channel_id, msg["ts"])
                    # replies[0] is the root message already in raw_messages — skip it
                    for reply in replies[1:]:
                        tagged_reply = {**reply, "_channel_id": channel_id}
                        thread_replies.append(tagged_reply)
                        msg_lookup[reply["ts"]] = tagged_reply
                except SlackClientError as exc:
                    logger.warning(
                        "scan_slack_channels: cannot fetch thread %s in %s: %s",
                        msg["ts"], channel_id, exc,
                    )

        for raw in list(raw_messages) + thread_replies:
            ts = raw.get("ts", "")
            text = raw.get("text", "").strip()
            user_id = raw.get("user", "")
            if not ts or not text or not user_id:
                continue

            reaction_count = sum(r.get("count", 0) for r in raw.get("reactions", []))

            slack_messages.append(SlackMessage(
                source_id=ts,
                channel_id=channel_id,
                user_id=user_id,
                text=text,
                thread_ts=raw.get("thread_ts"),
                reaction_count=reaction_count,
            ))

    return slack_messages, msg_lookup


def _upsert_embeddings(
    workspace_id: str,
    embed_meta: list[dict],
    embeddings: list[list[float]],
) -> None:
    """Upsert slack_message_embedding rows. Skips on conflict (idempotent)."""
    from app.db_sync import get_sync_pool

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            for meta, emb in zip(embed_meta, embeddings):
                vec_str = "[" + ",".join(str(x) for x in emb) + "]"
                cur.execute(
                    """
                    INSERT INTO slack_message_embedding
                        (id, workspace_id, channel_id, message_ts, author_id, text, embedding)
                    VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (workspace_id, channel_id, message_ts) DO NOTHING
                    """,
                    (
                        str(uuid4()),
                        workspace_id,
                        meta["channel_id"],
                        meta["ts"],
                        meta["user_id"],
                        meta["text"],
                        vec_str,
                    ),
                )
        conn.commit()
        logger.info("scan_slack_channels: upserted %d embeddings for workspace %s", len(embed_meta), workspace_id)
    except Exception as exc:
        conn.rollback()
        logger.error("scan_slack_channels: embedding upsert failed for %s: %s", workspace_id, exc)
    finally:
        pool.putconn(conn)


def _create_content_signal(
    workspace_id: str,
    candidate,
    msg_lookup: dict,
) -> str | None:
    """Insert a ContentSignal row. Returns the new signal_id or None on failure."""
    from app.db_sync import get_sync_pool

    source_messages = [
        {
            "ts": ts,
            "text": msg_lookup[ts].get("text", ""),
            "channel_id": msg_lookup[ts]["_channel_id"],
        }
        for ts in candidate.source_ids
        if ts in msg_lookup
    ]
    source_channel = source_messages[0]["channel_id"] if source_messages else None

    signal_id = str(uuid4())
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO content_signal
                    (id, workspace_id, source_type, source_id, source_channel,
                     signal_type, summary, status, raw_payload, metadata, sensitivity)
                VALUES
                    (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                """,
                (
                    signal_id,
                    workspace_id,
                    "slack",
                    candidate.source_ids[0],
                    source_channel,
                    candidate.signal_type,
                    candidate.summary,
                    "detected",
                    json.dumps({"source_ids": candidate.source_ids, "messages": source_messages}),
                    json.dumps({}),
                    "unknown",
                ),
            )
        conn.commit()
        return signal_id
    except Exception as exc:
        conn.rollback()
        logger.exception(
            "scan_slack_channels: failed to create ContentSignal for source_id %s: %s",
            candidate.source_ids[0], exc,
        )
        return None
    finally:
        pool.putconn(conn)


def _update_last_scanned(workspace_id: str) -> None:
    """Update workspace.settings.last_slack_scanned_at to now (UTC)."""
    from app.db_sync import get_sync_pool

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workspace
                SET settings = jsonb_set(
                    COALESCE(settings, '{}'::jsonb),
                    '{last_slack_scanned_at}',
                    %s::jsonb
                )
                WHERE id = %s::uuid
                """,
                (json.dumps(now_iso), workspace_id),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error(
            "scan_slack_channels: failed to update last_slack_scanned_at for %s: %s",
            workspace_id, exc,
        )
    finally:
        pool.putconn(conn)
