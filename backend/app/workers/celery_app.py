"""
Celery application factory for Vesper.

Queues
------
draft_pipeline  – sequential classify → enrich_context → generate pipeline
intake          – scheduled batch scans of Slack channels(2–3x/day via Celery Beat)
publishing      – LinkedIn post delivery
maintenance     – token refresh (Celery Beat), stale-record cleanup

Intake model (important)
------------------------
Auto content discovery is NOT event-driven. It runs as a scheduled batch scan so that
the classifier always has a window of accumulated messages with enough context to judge
content worthiness. Real-time Slack webhooks are used only for the manual
"Create LinkedIn draft" message action.
"""

import os

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.workers.constants import Queue as Q

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

celery_app = Celery(
    "vesper",
    broker=os.environ["REDIS_URL"],
    backend=os.environ["REDIS_URL"],
)

# ---------------------------------------------------------------------------
# Queue definitions
# ---------------------------------------------------------------------------

default_exchange = Exchange("default", type="direct")

TASK_QUEUES = (
    Queue(Q.DRAFT_PIPELINE, default_exchange, routing_key=Q.DRAFT_PIPELINE),
    Queue(Q.INTAKE, default_exchange, routing_key=Q.INTAKE),
    Queue(Q.PUBLISHING, default_exchange, routing_key=Q.PUBLISHING),
    Queue(Q.MAINTENANCE, default_exchange, routing_key=Q.MAINTENANCE),
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

celery_app.conf.update(
    # Queues
    task_queues=TASK_QUEUES,
    # No task_default_queue — tasks must always declare their queue explicitly.
    # This prevents accidentally landing on the wrong queue when queue= is omitted.
    task_default_exchange="default",
    # Routing: map each task module to its queue
    task_routes={
        "app.workers.draft_pipeline.*": {"queue": Q.DRAFT_PIPELINE},
        "app.workers.intake.*": {"queue": Q.INTAKE},
        "app.workers.publishing.*": {"queue": Q.PUBLISHING},
        "app.workers.maintenance.*": {"queue": Q.MAINTENANCE},
    },
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # One task per worker process at a time (keeps DB connections predictable)
    worker_prefetch_multiplier=1,
    # Result TTL
    result_expires=86_400,  # 24 h
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Beat schedule
    beat_schedule={
        # Fan-out Slack channel scans to all eligible workspaces — 2x/day
        "dispatch-intake-scans": {
            "task": "app.workers.maintenance.dispatch_intake_scans",
            "schedule": crontab(minute=0, hour="0,12"),
        },
        # Proactive LinkedIn token refresh — daily at 02:00 UTC
        "refresh-oauth-tokens": {
            "task": "app.workers.maintenance.refresh_oauth_tokens",
            "schedule": crontab(minute=0, hour=2),
        },
        # slack message embedding cleanup after 30 days — daily at 03:00 UTC
        "purge-slack-message-embeddings": {
            "task": "app.workers.maintenance.purge_slack_message_embeddings",
            "schedule": crontab(minute=0, hour=3),
        },
    },
)

# Eagerly import task modules so all tasks are registered before routing resolves.
# This is NOT autodiscovery — task names are explicit via name= on each decorator.
celery_app.autodiscover_tasks(
    [
        "app.workers.draft_pipeline",
        "app.workers.intake",
        "app.workers.publishing",
        "app.workers.maintenance",
    ]
)
