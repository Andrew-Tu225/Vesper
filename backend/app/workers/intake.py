"""
intake queue — scheduled batch content scanners (Celery Beat, 2–3x/day).

Why batch, not real-time
------------------------
A single Slack message or email rarely has enough context to judge content worthiness.
Running a scan on an accumulated window of messages gives the batch classifier the
conversational context it needs — threads, reactions, follow-ups — before deciding what
is worth drafting.

Slack Events API webhooks are used ONLY for the manual "Create LinkedIn draft" action.
Auto channel monitoring goes through this batch scanner, not webhooks.

Tasks
-----
scan_slack_channels   – fetch messages from workspace.settings.enrichment_channels
                        since last_slack_scanned_at, batch classify, create ContentSignals
                        for winners, dispatch draft_pipeline for each.

scan_gmail_inbox      – fetch emails from configured Gmail labels since
                        last_gmail_scanned_at, batch classify, same dispatch flow.

Scan checkpoint
---------------
Stored in workspace.settings (JSONB):
  last_slack_scanned_at : ISO-8601 UTC string
  last_gmail_scanned_at : ISO-8601 UTC string
  intake_runs_per_day   : int (default 3) — used by Celery Beat to compute interval

Batch classification
--------------------
Phase 2 will send the full fetched message list to GPT-4o-mini in a single call.
Structured output:
  [{"index": 0, "is_worthy": true, "signal_type": "customer_praise", "reason": "..."},
   {"index": 1, "is_worthy": false, "reason": "..."},
   ...]
Only worthy items become ContentSignals and enter the draft_pipeline queue.
"""

import logging

from app.workers.celery_app import celery_app
from app.workers.constants import Queue

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.intake.scan_slack_channels",
    queue=Queue.INTAKE,
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def scan_slack_channels(self, workspace_id: str) -> None:
    """Batch-scan configured Slack channels and create ContentSignals for worthy messages.

    Phase 2 implementation:
    1. Load workspace + settings (enrichment_channels, last_slack_scanned_at)
    2. For each channel, fetch messages since last_slack_scanned_at via Slack API
       - Include thread replies so classifier has full conversational context
    3. Send full message list to GPT-4o-mini batch classifier (one LLM call)
    4. For each message flagged as worthy:
       a. Create ContentSignal (status=detected, source_type=slack)
       b. Dispatch classify_signal task on draft_pipeline queue
    5. Update workspace.settings.last_slack_scanned_at = now()
    """
    logger.info("scan_slack_channels: workspace_id=%s (stub)", workspace_id)
    # Phase 2: implement batch scan


@celery_app.task(
    name="app.workers.intake.scan_gmail_inbox",
    queue=Queue.INTAKE,
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def scan_gmail_inbox(self, workspace_id: str) -> None:
    """Batch-scan Gmail labels and create ContentSignals for worthy emails.

    Phase 3 implementation:
    1. Load workspace + settings (gmail_labels, last_gmail_scanned_at)
    2. Fetch emails from configured labels since last_gmail_scanned_at
       using the workspace Gmail OAuth token (live API call, no local index)
    3. Send full email list to GPT-4o-mini batch classifier (one LLM call)
    4. For each email flagged as worthy:
       a. Create ContentSignal (status=detected, source_type=gmail)
       b. Dispatch classify_signal task on draft_pipeline queue
    5. Update workspace.settings.last_gmail_scanned_at = now()
    """
    logger.info("scan_gmail_inbox: workspace_id=%s (stub)", workspace_id)
    # Phase 3: implement batch scan
