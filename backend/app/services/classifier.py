"""
Batch classifier service — single GPT-4o-mini call for a channel scan window.

Design
------
- Input:  flat chronological list of SlackMessage objects from the scan window
- Output: list[ContentSignalCandidate] — worthy signals only (noise excluded)
- One LLM call per scan, regardless of message count
- A signal can span multiple messages (thread + replies, related messages)
- summary and signal_type are extracted in the same pass — no separate LLM call later

Usage
-----
    from app.services.classifier import batch_classify, ClassifierError
    from app.services.openai_client import SlackMessage

    try:
        candidates = await batch_classify(messages)
    except ClassifierError as exc:
        logger.error("classification failed: %s", exc)
        raise
"""

from __future__ import annotations

import logging

from openai import APIError

from app.config import settings
from app.services.openai_client import get_openai_client
from app.services.schemas import BatchClassifyResponse, ContentSignalCandidate, SlackMessage

logger = logging.getLogger(__name__)

SIGNAL_TYPES = (
    "customer_praise",
    "product_win",
    "launch_update",
    "hiring",
    "founder_insight",
)


class ClassifierError(Exception):
    """Raised when the LLM call fails after all retries are exhausted.

    The intake scanner task (scan_slack_channels) catches this and retries
    the whole scan via Celery's built-in retry mechanism.
    """


def _build_prompt(messages: list[SlackMessage]) -> str:
    """Render messages into an indexed, human-readable block for the LLM."""
    lines: list[str] = []
    for i, msg in enumerate(messages):
        thread_note = f" [thread:{msg.thread_ts}]" if msg.thread_ts else ""
        reaction_note = f" [reactions:{msg.reaction_count}]" if msg.reaction_count else ""
        lines.append(f"[{i}] id:{msg.source_id} channel:{msg.channel_id} user:{msg.user_id}{thread_note}{reaction_note}")
        lines.append(f"    {msg.text}")
    return "\n".join(lines)


async def batch_classify(messages: list[SlackMessage]) -> BatchClassifyResponse:
    """Classify a batch of Slack messages and return worthy content signal candidates.

    LLM reads the Slack message conversation flow, analyze and classify worthy content 
    signal from the messages, and then group the related message together for each signal
    and form ContentSignalCandidate

    Args:
        messages: Flat chronological list from the channel scan window.
                  May include messages from multiple channels and threads.

    Returns:
        List of ContentSignalCandidate. Empty list if nothing is worthy.

    Raises:
        ClassifierError: On API failure. Caller is responsible for retry.
    """
    if not messages:
        return BatchClassifyResponse(candidates=[], embed_message_ids=[])

    message_block = _build_prompt(messages)
    system_prompt = """\
You are a Content Signal Classifier for a LinkedIn content assistant used by early-stage startups.

## Role
Startups generate valuable content every day inside their Slack workspaces — customer wins, \
product milestones, team growth, founder lessons — but that content stays trapped internally. \
You have two jobs: surface moments worth turning into LinkedIn posts, and flag messages worth \
storing as context so future drafting has the full picture.

## Input Format
You will receive a chronological stream of internal Slack messages. Each message has:
  - id:          Unique Slack timestamp (e.g. 1712500000.000001). \
Use this exact value in all output — never invent or approximate.
  - channel:     The channel the message was posted in.
  - user:        The Slack user ID of the author.
  - [thread:X]   This message is a reply in the thread started by message id X.
  - [reactions:N] Total emoji reactions. High counts (5+) signal team excitement.
  - text:        The message body.

## Task 1 — Identify Content Signals
Read the message stream and identify clusters worth turning into a LinkedIn post. \
A cluster is one or more related messages (a thread, a back-and-forth exchange) that \
together form a single publishable moment.

Only classify a cluster as a signal if it clearly fits one of these types:

  customer_praise
    A customer expressed specific satisfaction, shared a success story, or praised the \
product. Generic internal "great job" comments do not qualify. \
Example: "Acme said our export feature saves their team 3 hours a week."

  product_win
    A concrete product milestone, significant feature shipped, or measurable technical \
achievement. Must include a specific outcome. \
Example: "We crossed 1,000 paying customers" or "Search latency is now under 50ms."

  launch_update
    A product, feature, integration, or service going live or being announced externally. \
Must be something released or actively shipping. \
Example: "API v2 is live for all customers today."

  hiring
    An open role, team growth announcement, or culture highlight compelling to a general \
LinkedIn audience. Example: "We're hiring our first ML engineer."

  founder_insight
    A founder or senior leader sharing a genuine lesson, contrarian opinion, strategic \
decision, or reflection on building the company. Must be substantive — not logistics. \
Example: "We almost killed this feature three times. Here's what made us keep it."

Selection rules:
- Group related messages (thread + replies, back-and-forth) into one signal. \
Include all contributing ids in source_ids.
- Be selective. Exclude internal ops, vague celebrations without specifics, \
work-in-progress with no outcome, and one-word or emoji-only reactions.
- High reaction counts increase the likelihood a cluster is post-worthy.
- If nothing qualifies, return an empty candidates list. Do not force signals.

## Task 2 — Identify Context Messages for Storage
Flag individual messages worth embedding for future semantic retrieval. \
These give the drafting agent context that may span multiple days of conversation — \
not just the current scan window. A message does not need to qualify as a content \
signal to be worth storing.

Include messages that carry domain-specific information:
- Work being done: technical decisions, implementations, approaches, blockers, breakthroughs
- Customer or user interactions, even brief ("Acme renewed", "user said login was confusing")
- Concrete outcomes or metrics ("we hit 1000 users", "latency down to 40ms")
- Product thinking, priorities, or strategic decisions from anyone on the team

Exclude messages with no informational value:
- Reactions and acknowledgements: "sounds good", "ok", "noted", "thanks", "+1", emoji-only
- Scheduling and logistics with no context attached: "call at 3pm", "brb", "out today"
- Messages that are only a bare URL with no surrounding explanation

Always include all source_ids from Task 1 candidates in this list — \
signal-worthy messages are always worth storing as context.

## Output
Return a single JSON object with two fields:

  candidates        List of content signals from Task 1. For each signal:
    source_ids        All message ids that form this signal (root + relevant replies).
    signal_type       One of: customer_praise, product_win, launch_update, hiring, founder_insight.
    summary           1–2 sentences as a brief for a copywriter. Be specific — include the \
outcome, customer name if mentioned, or metric. Used as the starting point for draft generation.
    reason            One sentence on why this is post-worthy. Internal logging only.

  embed_message_ids  Flat list of message ids from Task 2 (includes all candidate source_ids).\
"""
    user_prompt = (
        f"Below are {len(messages)} Slack messages from a recent channel scan. "
        "Identify content signals worth turning into LinkedIn posts (candidates), "
        "and messages worth storing for future semantic context retrieval (embed_message_ids). "
        "Return empty lists if nothing qualifies.\n\n"
        f"{message_block}"
    )

    client = get_openai_client()
    try:
        response = await client.beta.chat.completions.parse(
            model=settings.model_classify,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=BatchClassifyResponse,
            temperature=0,
        )
    except APIError as exc:
        raise ClassifierError(f"OpenAI API error during batch classification: {exc}") from exc

    result = response.choices[0].message.parsed
    if result is None:
        raise ClassifierError("LLM returned no parsed content — possible refusal or malformed response")

    # Validate signal_type values — drop any the LLM hallucinated
    valid: list[ContentSignalCandidate] = []
    for candidate in result.candidates:
        if candidate.signal_type not in SIGNAL_TYPES:
            logger.warning(
                "batch_classify: dropping candidate with unknown signal_type=%r source_ids=%s",
                candidate.signal_type,
                candidate.source_ids,
            )
            continue
        if not candidate.source_ids:
            logger.warning("batch_classify: dropping candidate with empty source_ids")
            continue
        valid.append(candidate)

    logger.info(
        "batch_classify: %d messages → %d candidates, %d messages flagged for embedding",
        len(messages),
        len(valid),
        len(result.embed_message_ids),
    )
    return BatchClassifyResponse(candidates=valid, embed_message_ids=result.embed_message_ids)
