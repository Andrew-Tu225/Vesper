"""
Enrichment agent eval — three layers in order of cost:

  1. Schema invariants     — free, always run — output is prose, iterations in budget
  2. Content verification  — briefing contains key facts from gold labels
  3. LLM judge             — optional (set EVAL_LLM_JUDGE=1)

Run fast checks only:
    pytest tests/eval/test_enrich_eval.py -m "not llm_judge"

Run everything including LLM judge:
    EVAL_LLM_JUDGE=1 pytest tests/eval/test_enrich_eval.py
"""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import pytest

import app.services.drafter as drafter_module
from app.services.drafter import run_enrich_agent

RUN_LLM_JUDGE = os.getenv("EVAL_LLM_JUDGE", "0") == "1"

_MAX_ITERATIONS = 5


def _build_source_messages(scenario, gold_candidate) -> list[dict]:
    """Build source_messages list for the enrichment agent from a scenario + gold candidate."""
    msg_lookup = {m.source_id: m for m in scenario.messages}
    result = []
    for sid in gold_candidate.source_ids:
        msg = msg_lookup.get(sid)
        if msg:
            result.append({
                "ts": msg.source_id,
                "channel_id": msg.channel_id,
                "text": msg.text,
            })
    return result


def _normalize(text: str) -> str:
    return re.sub(r"(\d),(\d)", r"\1\2", text.lower())


# ---------------------------------------------------------------------------
# Layer 1: Schema invariants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enrich_schema_invariants(signal_scenarios, mock_search_fn, mock_slack_client):
    """Enrichment output must be non-empty prose within the iteration budget."""
    errors: list[str] = []

    with patch("app.services.slack_client.get_workspace_client", return_value=mock_slack_client):
        for scenario in signal_scenarios:
            for gold_candidate in scenario.gold.candidates:
                source_messages = _build_source_messages(scenario, gold_candidate)
                summary = " ".join(gold_candidate.summary_must_contain[:3]) or "signal detected"

                context, iterations = await run_enrich_agent(
                    workspace_id=scenario.scenario_id,
                    summary=summary,
                    signal_type=gold_candidate.signal_type,
                    source_messages=source_messages,
                    search_fn=mock_search_fn,
                )

                key = f"{scenario.scenario_id} [{gold_candidate.signal_type}]"

                if not context or len(context.strip()) < 50:
                    errors.append(f"{key}: output too short ({len(context)} chars)")

                if not (1 <= iterations <= _MAX_ITERATIONS):
                    errors.append(
                        f"{key}: iteration count out of bounds ({iterations}), "
                        f"expected 1–{_MAX_ITERATIONS}"
                    )

    assert not errors, "Enrichment schema failures:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Layer 2: Content verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enrich_briefing_key_facts(signal_scenarios, mock_search_fn, mock_slack_client):
    """Enrichment briefing must mention at least half the required key facts from gold."""
    failures: list[str] = []

    with patch("app.services.slack_client.get_workspace_client", return_value=mock_slack_client):
        for scenario in signal_scenarios:
            for gold_candidate in scenario.gold.candidates:
                if not gold_candidate.summary_must_contain:
                    continue

                source_messages = _build_source_messages(scenario, gold_candidate)
                summary = " ".join(gold_candidate.summary_must_contain[:3])

                context, _ = await run_enrich_agent(
                    workspace_id=scenario.scenario_id,
                    summary=summary,
                    signal_type=gold_candidate.signal_type,
                    source_messages=source_messages,
                    search_fn=mock_search_fn,
                )

                context_norm = _normalize(context)
                missing = [
                    fact for fact in gold_candidate.summary_must_contain
                    if _normalize(fact) not in context_norm
                ]
                threshold = len(gold_candidate.summary_must_contain) / 2
                if len(missing) > threshold:
                    failures.append(
                        f"{scenario.scenario_id} [{gold_candidate.signal_type}]: "
                        f"briefing missing {len(missing)}/{len(gold_candidate.summary_must_contain)} "
                        f"key facts (>{threshold:.0f} allowed): {missing}\n"
                        f"  context: {context[:200]}"
                    )

    if failures:
        print(f"\nEnrichment key-fact failures ({len(failures)}):")
        for f in failures:
            print(f"  {f}")

    total_signals = sum(
        len(s.gold.candidates)
        for s in signal_scenarios
        if any(c.summary_must_contain for c in s.gold.candidates)
    )
    assert len(failures) / max(total_signals, 1) <= 0.30, (
        f"{len(failures)}/{total_signals} enrichment briefings missing required key facts "
        "(threshold: 30%)"
    )


@pytest.mark.asyncio
async def test_enrich_seeks_context_when_thin(signal_scenarios, mock_search_fn, mock_slack_client):
    """When source_messages is empty, the agent must make at least one tool call."""
    tool_calls_made: list[str] = []
    original_fn = drafter_module._execute_enrich_tool

    async def tracking_execute(tool_name, tool_args, workspace_id, slack_client, search_fn):
        tool_calls_made.append(tool_name)
        return await original_fn(tool_name, tool_args, workspace_id, slack_client, search_fn)

    scenario = signal_scenarios[0]
    gold_candidate = scenario.gold.candidates[0]

    with patch("app.services.slack_client.get_workspace_client", return_value=mock_slack_client):
        with patch.object(drafter_module, "_execute_enrich_tool", side_effect=tracking_execute):
            await run_enrich_agent(
                workspace_id=scenario.scenario_id,
                summary=f"potential {gold_candidate.signal_type} signal detected",
                signal_type=gold_candidate.signal_type,
                source_messages=[],
                search_fn=mock_search_fn,
            )

    assert tool_calls_made, (
        f"Agent made no tool calls despite empty source_messages for {scenario.scenario_id}. "
        "Expected at least one search_context or get_slack_thread call."
    )


# ---------------------------------------------------------------------------
# Layer 3: LLM judge
# ---------------------------------------------------------------------------

@pytest.mark.llm_judge
@pytest.mark.skipif(not RUN_LLM_JUDGE, reason="Set EVAL_LLM_JUDGE=1 to run LLM judge evals")
@pytest.mark.asyncio
async def test_enrich_quality_llm_judge(signal_scenarios, mock_search_fn, mock_slack_client):
    """Use GPT-4o-mini to score enrichment briefings on concreteness and ghostwriter utility."""
    from pydantic import BaseModel

    from app.services.openai_client import get_openai_client

    class BriefingScore(BaseModel):
        concreteness: int        # 1-5: does it name specific details (names, numbers, quotes)?
        ghostwriter_utility: int # 1-5: would a ghostwriter have what they need for a LinkedIn post?
        reasoning: str

    client = get_openai_client()
    scores: list[dict] = []

    with patch("app.services.slack_client.get_workspace_client", return_value=mock_slack_client):
        for scenario in signal_scenarios:
            for gold_candidate in scenario.gold.candidates:
                source_messages = _build_source_messages(scenario, gold_candidate)
                summary = " ".join(gold_candidate.summary_must_contain[:3]) or "signal detected"

                context, iterations = await run_enrich_agent(
                    workspace_id=scenario.scenario_id,
                    summary=summary,
                    signal_type=gold_candidate.signal_type,
                    source_messages=source_messages,
                    search_fn=mock_search_fn,
                )

                judge_response = await client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are evaluating a briefing written by a content enrichment agent. "
                                "The briefing is meant to help a ghostwriter draft a founder's LinkedIn post."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Signal type: {gold_candidate.signal_type}\n"
                                f"Briefing:\n{context}\n\n"
                                "Score 1-5:\n"
                                "concreteness: Does the briefing mention specific details "
                                "(customer names, metrics, timelines, direct quotes)? "
                                "1=entirely vague, 5=packed with specifics\n"
                                "ghostwriter_utility: If you were writing a LinkedIn post, "
                                "would this briefing give you what you need? "
                                "1=useless, 5=everything needed"
                            ),
                        },
                    ],
                    response_format=BriefingScore,
                    temperature=0,
                )
                score = judge_response.choices[0].message.parsed
                if score:
                    scores.append({
                        "scenario_id": scenario.scenario_id,
                        "signal_type": gold_candidate.signal_type,
                        "iterations": iterations,
                        "concreteness": score.concreteness,
                        "ghostwriter_utility": score.ghostwriter_utility,
                        "reasoning": score.reasoning,
                        "context": context[:150],
                    })

    print("\n\nLLM Judge — Enrichment Quality")
    print("=" * 90)
    for s in scores:
        print(
            f"{s['scenario_id']} [{s['signal_type']}] iters={s['iterations']} "
            f"conc={s['concreteness']}/5 util={s['ghostwriter_utility']}/5"
        )
        print(f"  {s['context']}")
        print(f"  judge: {s['reasoning'][:80]}")

    if scores:
        avg_conc = sum(s["concreteness"] for s in scores) / len(scores)
        avg_util = sum(s["ghostwriter_utility"] for s in scores) / len(scores)
        print(f"\nAverage concreteness:         {avg_conc:.2f}/5")
        print(f"Average ghostwriter utility:  {avg_util:.2f}/5")

        assert avg_conc >= 3.0, f"Average concreteness {avg_conc:.2f} is below 3.0"
        assert avg_util >= 3.0, f"Average ghostwriter utility {avg_util:.2f} is below 3.0"
