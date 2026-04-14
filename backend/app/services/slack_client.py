"""
Workspace-scoped synchronous Slack WebClient wrapper.

All Slack API calls in the application go through this module. Workers and services
import the public functions here rather than calling slack_sdk directly.

Why synchronous
---------------
Celery workers run in a sync process. AsyncWebClient requires a running event loop
and is not safe to use inside Celery tasks. slack_sdk.WebClient (sync) is the
correct choice for all worker code.

Layers
------
- get_workspace_client   Decrypt the workspace's bot token from the DB and return a
                         configured WebClient. Entry point for all callers.
- Layer 1 (private)      Raw Slack API calls with pagination. Never called directly
                         outside this module.
- Layer 2 (intake)       Public wrappers for the batch intake scanner. Called by
                         workers/intake.scan_slack_channels with precise timestamps.
- Posting                post_message / update_message for approval card management.
                         Called by workers/draft_pipeline.generate_draft and
                         services/approval.py.
- Agent tools            SLACK_ENRICHMENT_TOOLS schema + dispatch_slack_tool — deferred
                         to Phase 2.8 when enrich_context agent loop is implemented.

Usage
-----
    from app.services.slack_client import get_workspace_client, get_channel_history

    client = get_workspace_client(workspace_id)
    messages = get_channel_history(client, channel_id, oldest=1712500000.0, limit=200)
"""

from __future__ import annotations

import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.crypto import EncryptedToken, TokenDecryptionError, decrypt
from app.db_sync import get_sync_pool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SlackClientError(Exception):
    """Raised when a Slack API call fails or the workspace token cannot be loaded.

    Callers (Celery tasks) should catch this and trigger a task retry.
    """


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------

def get_workspace_client(workspace_id: str) -> WebClient:
    """Return a WebClient initialised with the workspace's Slack bot token.

    Loads the encrypted bot token from oauth_token, decrypts it using AES-256-GCM,
    and returns a configured synchronous WebClient.

    Called at the start of:
    - workers/intake.scan_slack_channels     (one call per workspace scan)
    - workers/draft_pipeline.enrich_context  (one call per enrichment run)

    Raises:
        SlackClientError: If no bot token row exists for the workspace, or if
                          decryption fails (key mismatch / data corruption).
    """
    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT encrypted_token, nonce, tag
                FROM oauth_token
                WHERE workspace_id = %s::uuid
                  AND provider = 'slack'
                  AND token_type = 'bot'
                  AND user_id IS NULL
                LIMIT 1
                """,
                (workspace_id,),
            )
            row = cur.fetchone()
    finally:
        pool.putconn(conn)

    if row is None:
        raise SlackClientError(
            f"No Slack bot token found for workspace {workspace_id}"
        )

    encrypted = EncryptedToken(
        ciphertext=bytes(row[0]),
        nonce=bytes(row[1]),
        tag=bytes(row[2]),
    )
    try:
        bot_token = decrypt(encrypted)
    except TokenDecryptionError as exc:
        raise SlackClientError(
            f"Failed to decrypt Slack token for workspace {workspace_id}"
        ) from exc

    return WebClient(token=bot_token)


# ---------------------------------------------------------------------------
# Layer 1 — private raw API calls
# ---------------------------------------------------------------------------

def _handle_api_error(api_method: str, context: str, exc: SlackApiError) -> None:
    """Log and re-raise a SlackApiError as SlackClientError.

    Logs the Retry-After header on rate-limit errors so callers can observe it
    in logs when tuning task retry delays.
    """
    error = exc.response.get("error", "unknown")
    if error == "ratelimited":
        retry_after = exc.response.headers.get("Retry-After", "unknown")
        logger.warning(
            "%s rate-limited for %s — Retry-After: %s",
            api_method, context, retry_after,
        )
    else:
        logger.error("%s failed for %s — slack error: %s", api_method, context, error)
    raise SlackClientError(f"{api_method} failed: {error}") from exc


def _fetch_channel_history(
    client: WebClient,
    channel_id: str,
    oldest: float,
    limit: int,
) -> list[dict]:
    """Fetch messages from a channel since oldest (Unix timestamp), up to limit.

    Handles cursor-based pagination transparently and stops once limit is reached
    or Slack signals no more pages.
    """
    messages: list[dict] = []
    cursor: str | None = None

    while True:
        kwargs: dict = {
            "channel": channel_id,
            "oldest": str(oldest),
            "limit": min(limit - len(messages), 200),  # Slack max per page is 200
        }
        if cursor:
            kwargs["cursor"] = cursor

        try:
            response = client.conversations_history(**kwargs)
        except SlackApiError as exc:
            _handle_api_error("conversations.history", channel_id, exc)

        messages.extend(response["messages"])

        if len(messages) >= limit:
            break

        next_cursor = (response.get("response_metadata") or {}).get("next_cursor", "")
        if not next_cursor:
            break
        cursor = next_cursor

    return messages[:limit]


def _fetch_thread_replies(
    client: WebClient,
    channel_id: str,
    thread_ts: str,
) -> list[dict]:
    """Fetch all messages in a thread (root + replies), handling pagination.

    The first element returned by conversations.replies is always the root message,
    followed by its replies in chronological order.
    """
    messages: list[dict] = []
    cursor: str | None = None

    while True:
        kwargs: dict = {
            "channel": channel_id,
            "ts": thread_ts,
            "limit": 200,
        }
        if cursor:
            kwargs["cursor"] = cursor

        try:
            response = client.conversations_replies(**kwargs)
        except SlackApiError as exc:
            _handle_api_error("conversations.replies", thread_ts, exc)

        messages.extend(response["messages"])

        next_cursor = (response.get("response_metadata") or {}).get("next_cursor", "")
        if not next_cursor:
            break
        cursor = next_cursor

    return messages


# ---------------------------------------------------------------------------
# Layer 2 — intake scanner interface
# ---------------------------------------------------------------------------

def get_channel_history(
    client: WebClient,
    channel_id: str,
    oldest: float,
    limit: int = 200,
) -> list[dict]:
    """Return messages posted in channel_id since oldest (Unix timestamp float).

    Called by workers/intake.scan_slack_channels for each channel ID in
    workspace.settings.enrichment_channels. oldest comes from
    WorkspaceSettings.last_slack_scanned_at converted to a Unix timestamp.

    Args:
        client:     WebClient from get_workspace_client().
        channel_id: Slack channel ID (e.g. "C01ABC123").
        oldest:     Unix timestamp float — fetch messages newer than this.
                    Typically datetime.timestamp() of last_slack_scanned_at.
        limit:      Maximum total messages to return across all pages.

    Returns:
        List of raw Slack message dicts in chronological order.

    Raises:
        SlackClientError: On Slack API failure.
    """
    return _fetch_channel_history(client, channel_id, oldest, limit)


def get_thread_replies(
    client: WebClient,
    channel_id: str,
    thread_ts: str,
) -> list[dict]:
    """Return all messages in a thread (root message + replies).

    Called by workers/intake.scan_slack_channels for each root message from
    get_channel_history that has reply_count > 0. Threads give the batch
    classifier the team's reaction and follow-up detail needed to judge
    content worthiness.

    Also called by workers/draft_pipeline.enrich_context when the enrichment
    agent requests additional thread context via the agent tool interface
    (Phase 2.8).

    Args:
        client:    WebClient from get_workspace_client().
        channel_id: Slack channel ID the thread belongs to.
        thread_ts: Timestamp of the thread's root message.

    Returns:
        List of raw Slack message dicts: [root_message, reply_1, reply_2, ...].

    Raises:
        SlackClientError: On Slack API failure.
    """
    return _fetch_thread_replies(client, channel_id, thread_ts)


# ---------------------------------------------------------------------------
# Approval card interface
# ---------------------------------------------------------------------------

def post_message(
    client: WebClient,
    channel: str,
    blocks: list[dict],
    text: str,
) -> str:
    """Post a Block Kit message and return its message_ts.

    Called by workers/draft_pipeline.generate_draft to post the approval card
    to workspace.settings.social_queue_channel after draft variants are created.
    The returned message_ts is stored on DraftPost.slack_message_ts so the card
    can be updated by the approval service.

    Args:
        client:  WebClient from get_workspace_client().
        channel: Channel name or ID (e.g. "vesper-ai" or "C01ABC123").
        blocks:  Block Kit blocks list for the approval card UI.
        text:    Plain-text fallback shown in notifications and accessibility contexts.

    Returns:
        message_ts of the posted message (e.g. "1712500000.000001").

    Raises:
        SlackClientError: On Slack API failure.
    """
    try:
        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=text,
        )
    except SlackApiError as exc:
        _handle_api_error("chat.postMessage", channel, exc)

    return response["ts"]


def update_message(
    client: WebClient,
    channel: str,
    ts: str,
    blocks: list[dict],
) -> None:
    """Update an existing Slack message with new Block Kit blocks.

    Called by services/approval.py after each approval action (approve, reject,
    rewrite, schedule) to replace the action buttons on the card with a status
    indicator (e.g. "✅ Approved by @user").

    Args:
        client:  WebClient from get_workspace_client().
        channel: Channel ID where the original message was posted.
        ts:      message_ts of the message to update (from DraftPost.slack_message_ts).
        blocks:  Replacement Block Kit blocks reflecting the new state.

    Raises:
        SlackClientError: On Slack API failure.
    """
    try:
        client.chat_update(
            channel=channel,
            ts=ts,
            blocks=blocks,
        )
    except SlackApiError as exc:
        _handle_api_error("chat.update", ts, exc)
