"""
maintenance queue — scheduled housekeeping tasks (Celery Beat).

Tasks
-----
- refresh_oauth_tokens : proactively refresh tokens expiring within 24 h
- cleanup_stale_signals: move stuck signals to 'failed' after a timeout
"""

import logging

from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery Beat schedule (add to celery_app.conf.beat_schedule in Phase 6)
# ---------------------------------------------------------------------------
# "refresh-oauth-tokens": {
#     "task": "app.workers.maintenance.refresh_oauth_tokens",
#     "schedule": crontab(minute=0, hour="*/6"),  # every 6 h
# },
# "cleanup-stale-signals": {
#     "task": "app.workers.maintenance.cleanup_stale_signals",
#     "schedule": crontab(minute=30, hour=2),      # daily at 02:30 UTC
# },


@celery_app.task(
    name="app.workers.maintenance.refresh_oauth_tokens",
    queue=Queue.MAINTENANCE,
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def refresh_oauth_tokens(self) -> None:
    """Proactively refresh Slack / LinkedIn OAuth tokens expiring within 24 h.

    Phase 6: query oauth_token table, call provider refresh endpoints,
    re-encrypt and persist updated tokens.
    """
    logger.info("refresh_oauth_tokens: (stub)")


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
