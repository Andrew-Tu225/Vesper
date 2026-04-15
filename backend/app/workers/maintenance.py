"""
maintenance queue — scheduled housekeeping tasks (Celery Beat).

Tasks
-----
- dispatch_intake_scans      : fan-out scan_slack_channels to every eligible workspace (2x/day)
- refresh_oauth_tokens       : proactively refresh LinkedIn tokens expiring within 7 days
- cleanup_stale_signals      : move stuck signals to 'failed' after a timeout
- purge_slack_message_embeddings: delete embedding rows older than 30 days
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.maintenance.dispatch_intake_scans",
    queue=Queue.MAINTENANCE,
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def dispatch_intake_scans(self) -> None:
    """Fan-out scan_slack_channels to every eligible workspace.

    Eligibility criteria (checked in SQL for atomicity):
    - onboarding_complete = TRUE
    - subscription_status = 'active'
      OR (subscription_status = 'trialing' AND trial_ends_at > now())
    - enrichment_channels in settings is a non-empty JSON array

    Runs 2x/day via Celery Beat at 00:00 and 12:00 UTC.
    Each workspace has its own Slack bot token, so scans run in parallel
    without sharing rate-limit quotas.
    """
    from app.db_sync import get_sync_pool
    from app.workers.intake import scan_slack_channels

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text FROM workspace
                WHERE onboarding_complete = TRUE
                  AND (
                    subscription_status = 'active'
                    OR (
                      subscription_status = 'trialing'
                      AND trial_ends_at > now()
                    )
                  )
                  AND settings->'enrichment_channels' IS NOT NULL
                  AND jsonb_array_length(settings->'enrichment_channels') > 0
                """
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("dispatch_intake_scans: failed to query eligible workspaces: %s", exc)
        raise self.retry(exc=exc)
    finally:
        pool.putconn(conn)

    workspace_ids = [row[0] for row in rows]
    logger.info("dispatch_intake_scans: dispatching %d workspace(s)", len(workspace_ids))

    for workspace_id in workspace_ids:
        scan_slack_channels.delay(workspace_id)


@celery_app.task(
    name="app.workers.maintenance.refresh_oauth_tokens",
    queue=Queue.MAINTENANCE,
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def refresh_oauth_tokens(self) -> None:
    """Proactively refresh LinkedIn OAuth tokens expiring within 7 days.

    Queries all linkedin_company refresh tokens expiring within the refresh
    window, calls LinkedIn's token refresh endpoint for each, and re-encrypts
    the updated tokens. Writes an AuditLog entry on success and failure.

    On failure, logs a warning — Phase 2 will add a Slack notification via
    the workspace's bot token once the Slack messaging layer is in place.
    """
    asyncio.run(_refresh_oauth_tokens_async())


async def _refresh_oauth_tokens_async() -> None:
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.oauth_token import OAuthToken
    from app.services.linkedin_oauth import refresh_token_for_workspace

    refresh_window = datetime.now(tz=timezone.utc) + timedelta(days=7)

    async with AsyncSessionLocal() as db:
        # Query ACCESS tokens expiring within the window. The access token (~60 days)
        # is what expires in normal operation. The refresh token (~365 days) is only
        # used as the credential to obtain a new access token — if it expires without
        # renewal that requires user re-authorization, which we cannot automate.
        expiring_access = await db.execute(
            select(OAuthToken).where(
                OAuthToken.provider == "linkedin_company",
                OAuthToken.token_type == "access",
                OAuthToken.expires_at > datetime.now(tz=timezone.utc),
                OAuthToken.expires_at < refresh_window,
            )
        )
        expiring_access_rows = expiring_access.scalars().all()

        if not expiring_access_rows:
            logger.info("refresh_oauth_tokens: no access tokens expiring within 7 days")
            return

        logger.info(
            "refresh_oauth_tokens: refreshing %d access token(s)", len(expiring_access_rows)
        )

        for access_row in expiring_access_rows:
            # Find the corresponding refresh token for this workspace
            refresh_result = await db.execute(
                select(OAuthToken).where(
                    OAuthToken.workspace_id == access_row.workspace_id,
                    OAuthToken.provider == "linkedin_company",
                    OAuthToken.token_type == "refresh",
                    OAuthToken.user_id == None,  # noqa: E711
                )
            )
            refresh_row = refresh_result.scalar_one_or_none()

            if refresh_row is None:
                logger.warning(
                    "refresh_oauth_tokens: no refresh token found for workspace %s — skipping",
                    access_row.workspace_id,
                )
                continue

            success = await refresh_token_for_workspace(db, refresh_row)

            if success:
                db.add(
                    AuditLog(
                        workspace_id=refresh_row.workspace_id,
                        entity_type="oauth_token",
                        entity_id=refresh_row.id,
                        action="token_refreshed",
                        actor="celery",
                        new_value={"provider": "linkedin_company", "token_type": "refresh"},
                    )
                )
                logger.info(
                    "refresh_oauth_tokens: refreshed tokens for workspace %s",
                    refresh_row.workspace_id,
                )
            else:
                db.add(
                    AuditLog(
                        workspace_id=refresh_row.workspace_id,
                        entity_type="oauth_token",
                        entity_id=refresh_row.id,
                        action="token_refresh_failed",
                        actor="celery",
                        new_value={"provider": "linkedin_company", "token_type": "refresh"},
                    )
                )
                logger.warning(
                    "refresh_oauth_tokens: FAILED to refresh tokens for workspace %s — "
                    "LinkedIn reconnect required. Phase 2 will send a Slack warning.",
                    refresh_row.workspace_id,
                )

        await db.commit()


@celery_app.task(
    name="app.workers.maintenance.cleanup_stale_signals",
    queue=Queue.MAINTENANCE,
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def cleanup_stale_signals(self) -> None:
    """Mark signals stuck in intermediate states as 'failed'.

    Phase 6: find signals that have not advanced within a configurable
    timeout (e.g. 24 h in 'classified' or 'enriched') and set status → failed.
    """
    logger.info("cleanup_stale_signals: (stub)")


@celery_app.task(
    name="app.workers.maintenance.purge_slack_message_embeddings",
    queue=Queue.MAINTENANCE,
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def purge_slack_message_embeddings(self) -> None:
    """Delete slack_message_embedding rows older than 30 days.

    Old messages lose relevance as enrichment context. Running daily at 03:00 UTC
    keeps the table bounded without impacting active enrichment queries.
    """
    from app.db_sync import get_sync_pool

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM slack_message_embedding"
                " WHERE stored_at < now() - interval '30 days'"
            )
            deleted = cur.rowcount
        conn.commit()
        logger.info("purge_slack_message_embeddings: deleted %d rows", deleted)
    except Exception as exc:
        conn.rollback()
        logger.exception("purge_slack_message_embeddings: failed")
        raise self.retry(exc=exc)
    finally:
        pool.putconn(conn)
