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


async def batch_classify(messages: list[SlackMessage]) -> list[ContentSignalCandidate]:
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
        return []

    message_block = _build_prompt(messages)
    system_prompt = """\
You are a Content Signal Classifier for a LinkedIn content assistant used by early-stage startups.

## Your Role
Startups generate valuable content every day inside their Slack workspaces — customer wins, \
product milestones, team growth, founder lessons — but that content stays trapped internally \
and never reaches their audience. Your job is to read through a stream of Slack messages and \
surface the ones that contain real content value: moments worth turning into a LinkedIn post \
that builds the company's public presence.

## What You Are Looking At
You will receive a chronological stream of Slack messages from a company's internal channels. \
Each message has:
  - id:        The unique Slack message timestamp (e.g. 1712500000.000001). \
Use this exact value when referencing a message in your output.
  - channel:   The Slack channel the message was posted in.
  - user:      The Slack user ID of the author.
  - [thread:X] If present, this message is a reply in the thread started by message id X. \
Thread replies give you the team's reaction and add context to the root message.
  - [reactions:N] The total number of emoji reactions on this message. \
High reaction counts (5+) are a strong signal that the team found this message important or exciting.
  - text:      The message body.

## Content Signal Types
Only classify a message cluster as a signal if it clearly fits one of these types:

  customer_praise
    A customer expressed genuine satisfaction, shared a success story, gave a testimonial, \
or praised the product or team. The praise must be specific — generic "great job" internal \
comments do not qualify. Example: "Just got off a call with Acme — they said our export \
feature saved their team 3 hours a week."

  product_win
    A notable product milestone, significant feature shipped, or measurable technical \
achievement. Must be concrete and specific. Example: "We just crossed 1,000 paying customers" \
or "Search latency is now under 50ms after the rewrite."

  launch_update
    A new product, feature, integration, or service going live or being announced externally. \
Must be something that is being released or has just shipped. Example: "The new API v2 is \
live for all customers starting today."

  hiring
    An open role, team growth announcement, or culture highlight that a general LinkedIn \
audience would find compelling. Example: "We're hiring our first ML engineer — looking for \
someone who thrives in ambiguity."

  founder_insight
    A founder or senior leader sharing a genuine lesson learned, a contrarian opinion, a \
strategic decision, or a reflection on building the company. Must be substantive and original — \
not just logistics or status updates. Example: "We almost killed this feature three times. \
Here's what made us keep it."

## Rules
1. A signal often spans multiple messages. A thread root plus its replies, or a series of \
related back-and-forth messages, should be grouped into a single signal. Include all \
contributing message ids in source_ids.
2. Be selective. Only surface signals with genuine external audience value. Exclude:
   - Internal ops and logistics (standups, scheduling, reminders)
   - Vague praise or celebrations with no specific context
   - Work-in-progress updates with no clear outcome
   - One-word or emoji-only reactions
3. Reaction counts matter. A message cluster with many reactions is more likely to be \
genuinely exciting and post-worthy.
4. source_ids must contain the exact id values from the message stream — never invent or \
approximate them.
5. If nothing in the stream qualifies, return an empty candidates list. Do not force signals.

## Output Format
For each signal you identify, return:

  source_ids   List of exact message ids (from the id: field) that together form this signal. \
Always include the root message. Include thread replies that add meaningful context.
  signal_type  One of the five types above: customer_praise, product_win, launch_update, \
hiring, founder_insight.
  summary      1–2 sentences written as a brief for a copywriter. Be specific — include the \
actual outcome, customer name (if mentioned), or metric. This will be used as the \
starting point for generating a LinkedIn post draft.
  reason       One sentence explaining why this qualifies as post-worthy content. \
Used for internal logging only — not shown to users.\
"""
    user_prompt = (
        f"Below are {len(messages)} Slack messages from a recent channel scan. "
        "Identify any content signals worth turning into LinkedIn posts. "
        "Return an empty candidates list if nothing qualifies.\n\n"
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

    candidates = result.candidates

    # Validate signal_type values — drop any the LLM hallucinated
    valid: list[ContentSignalCandidate] = []
    for candidate in candidates:
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
        "batch_classify: %d messages → %d candidates",
        len(messages),
        len(valid),
    )
    return valid
