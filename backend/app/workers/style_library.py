"""
style_library queue — embed and upsert approved posts into the style library.

Phase 2 will implement:
- embed_style_entry: call text-embedding-3-small, store pgvector embedding
- auto_add_on_publish: triggered after a post goes live
"""

import logging

from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.style_library.embed_style_entry",
    queue=Queue.STYLE_LIBRARY,
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def embed_style_entry(self, style_entry_id: str) -> str:
    """Generate and store the pgvector embedding for a style library entry.

    Phase 2: call OpenAI text-embedding-3-small, upsert into style_entry.embedding.
    """
    logger.info("embed_style_entry: style_entry_id=%s (stub)", style_entry_id)
    return style_entry_id
