"""
publishing queue — LinkedIn post delivery.

Phase 5 will implement:
- publish_post: POST to LinkedIn Marketing API, handle retries and token refresh.
- schedule_post: delay delivery until the requested datetime.
"""

import logging

from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.publishing.publish_post",
    queue=Queue.PUBLISHING,
    bind=True,
    max_retries=5,
    default_retry_delay=120,
)
def publish_post(self, draft_post_id: str) -> None:
    """Deliver an approved DraftPost to LinkedIn.

    Phase 5: call LinkedIn Marketing API, update DraftPost + ContentSignal
    status to 'posted'.
    """
    logger.info("publish_post: draft_post_id=%s (stub)", draft_post_id)
