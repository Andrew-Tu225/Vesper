"""
Draft pipeline async LLM helpers — enrichment agent, redaction, and generation.

All functions are async and called from Celery workers via asyncio.run().
They are extracted here to keep workers/draft_pipeline.py under 800 lines.

Public API
----------
run_enrich_agent   — GPT-4o-mini agent loop (max 5 iterations) with 2 tools:
                       get_slack_thread  — fetch Slack thread replies
                       search_context    — pgvector cosine search (30-day window)
run_redact         — GPT-4o-mini structured output; returns RedactResult
run_generate       — GPT-4o structured output; returns list[str] of post bodies
"""

from __future__ import annotations

import json
import logging

from openai import APIError

from app.config import settings
from app.services.openai_client import get_openai_client
from app.services.schemas import GenerateDraftResponse, RedactResult

logger = logging.getLogger(__name__)

__all__ = ["RedactError", "run_enrich_agent", "run_redact", "run_generate"]


class RedactError(Exception):
    """Raised when the redaction LLM call fails after retries."""

# ---------------------------------------------------------------------------
# Enrichment agent constants
# ---------------------------------------------------------------------------

_MAX_ENRICH_ITERATIONS = 5
_SEARCH_RESULT_LIMIT = 5
_CONTEXT_SUMMARY_MAX_CHARS = 8_000  # ~2,000 tokens — cost control

ENRICH_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_slack_thread",
            "description": (
                "Fetch all messages in a Slack thread. "
                "Use when you need the full conversation that produced the signal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Slack channel ID, e.g. C01ABC123",
                    },
                    "thread_ts": {
                        "type": "string",
                        "description": "Timestamp of the thread root message",
                    },
                },
                "required": ["channel_id", "thread_ts"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_context",
            "description": (
                "Semantic search over the last 30 days of stored Slack messages. "
                "Use to find prior discussions, earlier mentions, or background context "
                "that is not in the current thread."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query for what context you need",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Enrichment tool execution
# ---------------------------------------------------------------------------

async def _execute_enrich_tool(
    tool_name: str,
    tool_args: dict,
    workspace_id: str,
    slack_client,
    search_fn,
) -> str:
    """Execute one enrichment tool call; always returns a string.

    Failures are non-fatal — the agent receives an error string and can
    decide whether to retry or continue without the context.

    Args:
        tool_name:    "get_slack_thread" or "search_context"
        tool_args:    Parsed arguments dict from the LLM tool call
        workspace_id: Used by search_context for scoped pgvector query
        slack_client: sync WebClient, or None if Slack is unavailable
        search_fn:    Callable (workspace_id, vec) -> list[dict] — injected to
                      avoid circular imports from drafter → draft_pipeline
    """
    if tool_name == "get_slack_thread":
        channel_id = tool_args.get("channel_id", "")
        thread_ts = tool_args.get("thread_ts", "")
        if not channel_id or not thread_ts:
            return "Error: get_slack_thread requires both channel_id and thread_ts."
        if slack_client is None:
            return "Error: Slack client unavailable for this workspace."
        try:
            from app.services.slack_client import SlackClientError, get_thread_replies
            messages = get_thread_replies(slack_client, channel_id, thread_ts)
            lines = [
                f"[ts:{m.get('ts', '')}] user:{m.get('user', '?')} - {m.get('text', '').strip()}"
                for m in messages
                if m.get("text", "").strip()
            ]
            return "\n".join(lines) if lines else "Thread has no text messages."
        except Exception as exc:
            logger.warning("enrich tool get_slack_thread failed: %s", exc)
            return f"Error fetching thread: {exc}"

    if tool_name == "search_context":
        query = tool_args.get("query", "").strip()
        if not query:
            return "Error: search_context requires a non-empty query."
        try:
            from app.services.embedder import embed_texts
            embeddings = await embed_texts([query])
            results = search_fn(workspace_id, embeddings[0])
            if not results:
                return "No relevant context found in the last 30 days."
            lines = [
                f"[similarity:{r['similarity']:.2f} ts:{r['message_ts']}]\n  {r['text']}"
                for r in results
            ]
            return "\n\n".join(lines)
        except Exception as exc:
            logger.warning("enrich tool search_context failed: %s", exc)
            return f"Error searching context: {exc}"

    return f"Unknown tool: {tool_name}"


# ---------------------------------------------------------------------------
# Public async helpers
# ---------------------------------------------------------------------------

async def run_enrich_agent(
    workspace_id: str,
    summary: str,
    signal_type: str,
    source_messages: list[dict],
    search_fn,
) -> tuple[str, int]:
    """Run the enrichment agent loop.

    Args:
        workspace_id:    Used to scope Slack client + pgvector search
        summary:         Signal summary (from batch_classify)
        signal_type:     e.g. "product_win"
        source_messages: List of {ts, channel_id, text} dicts for every message
                         that forms this signal. Text is included so the agent has
                         the source content upfront without a tool call. channel_id
                         is per-message because signals can span multiple channels.
        search_fn:       _search_similar_messages(workspace_id, vec) — injected
                         from draft_pipeline to avoid circular imports

    Returns:
        (context_summary, iterations_used)
        Falls back to summary if the agent produces no prose output.
    """
    from app.services.slack_client import SlackClientError, get_workspace_client

    slack_client = None
    try:
        slack_client = get_workspace_client(workspace_id)
    except SlackClientError as exc:
        logger.warning("run_enrich_agent: Slack unavailable for %s: %s", workspace_id, exc)

    client = get_openai_client()
    system_prompt = """\
You are a context enrichment agent for a LinkedIn content assistant used by B2B startups.

## Your job
1. Read the signal type, summary, and source messages provided.
2. Judge whether there is enough context to write a compelling, specific LinkedIn post.
   A post needs at least: the core outcome or insight, one concrete detail (metric, quote,
   customer name, or timeline), and enough background to make the story coherent to an
   outside reader.
3. If context is insufficient, use the available tools to fill the gaps:
   - get_slack_thread  — fetch the full reply chain for a thread not yet shown
   - search_context    — semantic search over the last 30 days of stored Slack messages;
                         use this for prior discussions, earlier metrics, or background
                         that predates the current scan window
   Use tools only when they would add information not already present. Do not call a tool
   if the source messages already contain what you need.
4. When you have enough context, stop calling tools and produce your output.

## Output format
Respond with a single prose paragraph of 2-5 sentences. This paragraph will be passed
directly to a copywriter as their briefing. It must include:
- What happened (the outcome, decision, or insight)
- One specific detail (number, quote, customer name, or timeline) if available
- Any relevant background that makes the story land for someone outside the company
Be concrete. Do not pad. Do not repeat the summary verbatim.\
"""

    # Format source messages for the prompt: text upfront, channel_id available for tool calls
    source_block_lines: list[str] = []
    for m in source_messages[:10]:  # cap at 10 to avoid huge prompts
        source_block_lines.append(
            f"  [channel:{m['channel_id']} ts:{m['ts']}]\n  {m.get('text', '').strip()}"
        )
    source_block = "\n\n".join(source_block_lines) if source_block_lines else "(no source messages)"

    user_prompt = (
        f"Signal type: {signal_type}\n"
        f"Summary: {summary}\n\n"
        f"Source messages:\n{source_block}\n\n"
        "Assess whether the above is enough context for a specific LinkedIn post. "
        "Use tools if needed, then write the context_summary paragraph."
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    context_summary = summary  # fallback
    iterations = 0

    for iteration in range(_MAX_ENRICH_ITERATIONS):
        iterations = iteration + 1
        response = await client.chat.completions.create(
            model=settings.model_classify,
            messages=messages,
            tools=ENRICH_TOOLS,
            tool_choice="auto",
            temperature=0,
        )
        msg = response.choices[0].message

        assistant_entry: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if not msg.tool_calls:
            context_summary = msg.content or summary
            break

        for tc in msg.tool_calls:
            try:
                tool_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}
            result = await _execute_enrich_tool(
                tc.function.name, tool_args, workspace_id, slack_client, search_fn
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        # Iteration cap — harvest last assistant prose
        for entry in reversed(messages):
            if entry.get("role") == "assistant" and entry.get("content"):
                context_summary = entry["content"]
                break

    return context_summary, iterations


async def run_redact(original_text: str) -> RedactResult:
    """Call GPT-4o-mini to strip PII and sensitive details.

    Returns:
        RedactResult with redacted_text and sensitivity (low | medium | high)

    Raises:
        RedactError: On API failure or empty parsed response.
    """
    system_prompt = """\
You are a privacy and confidentiality reviewer for a B2B startup preparing internal Slack \
messages for use in LinkedIn post drafts.

## What to redact
Replace only content that would be genuinely harmful or inappropriate to make public:

- Full names of specific individuals (employees, customers, prospects) → [Person]
- Customer or partner company names (they haven't consented to being named) → [Customer]
- Specific financial figures that are internal-only: runway, burn rate, salaries, \
undisclosed deal dollar amounts → [Amount]
- Personal contact details: email addresses, phone numbers → [Contact]
- Internal project codenames not yet publicly announced → [Project]

## What to preserve
Do NOT redact content that is safe and valuable for a LinkedIn post:

- Metrics and outcomes: user counts, performance numbers, growth percentages, \
time savings — these are the substance of the post
- Product or feature names that are publicly available
- Role titles without names ("our CEO", "a customer", "the engineering team")
- General timeline references ("last month", "this quarter", "after six months")
- Industry context and general market observations
- Sentiment and outcomes, even if they mention the customer's reaction — \
just replace the company name if it appears

## Sensitivity rating
Set sensitivity based on what you found:
- low: No meaningful redactions needed; the text is safe as-is
- medium: Some names or specifics replaced, but the substance is fully intact
- high: Significant confidential content removed — financial figures, \
multiple customer names, or internal-only operational details

## Rules
- Keep the substance, tone, and all factual outcomes intact
- Use the smallest redaction that removes the risk — do not over-redact
- Do not rephrase, summarise, or add information not in the original\
"""
    user_prompt = (
        f"Review and redact the following internal message:\n\n{original_text}"
    )

    try:
        response = await get_openai_client().beta.chat.completions.parse(
            model=settings.model_classify,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=RedactResult,
            temperature=0,
        )
    except APIError as exc:
        raise RedactError(f"OpenAI API error during redaction: {exc}") from exc

    result = response.choices[0].message.parsed
    if result is None:
        raise RedactError("LLM returned no parsed result during redaction")

    return result


async def run_generate(
    summary: str,
    signal_type: str,
    context_summary: str,
    variant_count: int,
    source_messages: list[dict] | None = None,
) -> list[str]:
    """Call GPT-4o to generate LinkedIn post variants.

    Args:
        summary:         Signal summary from batch_classify (1–2 sentences).
        signal_type:     e.g. "product_win"
        context_summary: Enrichment agent output paragraph.
        variant_count:   How many post variants to produce.
        source_messages: Optional list of {ts, channel_id, text} dicts — the raw
                         Slack messages that form this signal. Included in the prompt
                         so GPT-4o has access to the original phrasing, specific
                         quotes, and teammate reactions rather than relying solely
                         on the LLM-abstracted summary + context.

    Returns exactly variant_count post bodies (pads with first variant if LLM
    returns fewer than requested).

    Raises:
        Exception: On API failure or empty response.
    """
    truncated_context = context_summary[:_CONTEXT_SUMMARY_MAX_CHARS]

    system_prompt = """\
You are a LinkedIn ghostwriter for a B2B startup founder or operator.

## Your job
You will be given a content signal — something meaningful that happened inside the company \
(a customer win, a product milestone, a team insight, a founder lesson). Your job is to turn \
it into a LinkedIn post that a real person would actually want to read and share.

## What you are given
- Signal type: the category of the moment (customer_praise, product_win, launch_update, \
hiring, founder_insight)
- Summary: a one or two sentence brief of what happened
- Context: enriched background from internal Slack — may include specific metrics, quotes, \
timelines, or customer details that did not make it into the summary

Use all three to write the post. The context often contains the specific detail that makes \
a post land — do not ignore it.

## How to write a good post
A good LinkedIn post has four qualities:

1. It opens with something real, not a preamble.
   The first line must make someone stop scrolling. Lead with the most interesting thing — \
a number, a confession, a counterintuitive observation, or a concrete outcome.
   Bad: "We're excited to share that we've hit a major milestone."
   Good: "1,000 paying customers. Eight months to the first 500. Three weeks to the next 500."

2. It is specific, not generic.
   Names, numbers, timelines, and quotes make a post believable and worth reading. \
A vague post about "growth" teaches nobody anything. Use the concrete details from the context.

3. It earns its length.
   Every sentence must add something. Aim for 100–200 words. Do not pad, recap, or repeat. \
No bullet lists unless the content is genuinely list-shaped (e.g. a step-by-step lesson).

4. It does not sound like marketing copy.
   No filler phrases: "thrilled to announce", "excited to share", "proud to say", \
"game-changing", "innovative solution". Write how a real person talks — direct and grounded.

## Format rules
- No hashtags unless they appear naturally in the signal itself
- No sign-off lines ("Feel free to reach out", "DM me", "Follow for more")
- No em-dash abuse — use it at most once per post
- First-person singular ("I", "we") — choose one and stay consistent within a variant\
"""

    source_block = ""
    if source_messages:
        lines = [
            m.get("text", "").strip()
            for m in source_messages[:10]
            if m.get("text", "").strip()
        ]
        if lines:
            source_block = "\n\nSource messages (raw Slack text):\n" + "\n\n".join(
                f"  {line}" for line in lines
            )

    user_prompt = (
        f"Signal type: {signal_type}\n"
        f"Summary: {summary}\n\n"
        f"Context:\n{truncated_context}"
        f"{source_block}\n\n"
        f"Write {variant_count} LinkedIn post variants. "
        "Each variant must take a different angle on the same moment:\n"
        "- Variant 1: lead with the result or number — start with the outcome, then explain it\n"
        "- Variant 2: lead with the journey or lesson — start from the struggle or the turning "
        "point, land on the outcome at the end\n"
        "Return only the post bodies, one per variant."
    )

    try:
        response = await get_openai_client().beta.chat.completions.parse(
            model=settings.model_generate,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=GenerateDraftResponse,
            temperature=0.7,
        )
    except APIError as exc:
        raise Exception(f"OpenAI API error during draft generation: {exc}") from exc

    result = response.choices[0].message.parsed
    if result is None or not result.variants:
        raise Exception("LLM returned no draft variants")

    variants = list(result.variants[:variant_count])
    while len(variants) < variant_count:
        variants.append(variants[0])

    return variants
