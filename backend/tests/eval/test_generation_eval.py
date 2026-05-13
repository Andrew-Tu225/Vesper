"""
Generation eval — three layers in order of cost:

  1. Schema invariants    — free, always run — variant count, word count, no banned phrases
  2. Structure compliance — hook/body/closing shape, concrete signal details
  3. LLM judge            — optional (set EVAL_LLM_JUDGE=1)

Run fast checks only:
    pytest tests/eval/test_generation_eval.py -m "not llm_judge"

Run everything including LLM judge:
    EVAL_LLM_JUDGE=1 pytest tests/eval/test_generation_eval.py
"""

from __future__ import annotations

import os
import re

import pytest

from app.services.drafter import run_generate

RUN_LLM_JUDGE = os.getenv("EVAL_LLM_JUDGE", "0") == "1"

VARIANT_COUNT = 2

BANNED_PHRASES = [
    "thrilled to announce",
    "thrilled to share",
    "excited to announce",
    "excited to share",
    "proud to announce",
    "proud to share",
    "game-changing",
    "game changer",
    "innovative solution",
    "feel free to reach out",
    "dm me",
    "follow for more",
    "we're excited",
    "we are excited",
]


def _build_generation_inputs(
    scenario, gold_candidate
) -> tuple[str, str, str, list[dict]]:
    """Derive (summary, signal_type, context_summary, source_messages) from a scenario."""
    msg_lookup = {m.source_id: m for m in scenario.messages}
    source_messages = [
        {"ts": m.source_id, "channel_id": m.channel_id, "text": m.text}
        for sid in gold_candidate.source_ids
        if (m := msg_lookup.get(sid))
    ]

    summary = gold_candidate.reason
    context_summary = (
        f"{gold_candidate.reason}. "
        + " ".join(m["text"] for m in source_messages[:3])
    )
    return summary, gold_candidate.signal_type, context_summary, source_messages


def _word_count(text: str) -> int:
    return len(text.split())


def _paragraphs(text: str) -> list[str]:
    """Split post into non-empty sections separated by blank lines."""
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def _normalize(text: str) -> str:
    return re.sub(r"(\d),(\d)", r"\1\2", text.lower())


# ---------------------------------------------------------------------------
# Layer 1: Schema invariants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generation_schema_invariants(signal_scenarios):
    """Generation must return the requested variant count; each post must be non-empty and sized."""
    errors: list[str] = []

    for scenario in signal_scenarios:
        for gold_candidate in scenario.gold.candidates:
            summary, signal_type, context_summary, source_messages = _build_generation_inputs(
                scenario, gold_candidate
            )

            variants = await run_generate(
                summary=summary,
                signal_type=signal_type,
                context_summary=context_summary,
                variant_count=VARIANT_COUNT,
                source_messages=source_messages,
            )

            key = f"{scenario.scenario_id} [{signal_type}]"

            if len(variants) != VARIANT_COUNT:
                errors.append(
                    f"{key}: expected {VARIANT_COUNT} variants, got {len(variants)}"
                )

            for i, variant in enumerate(variants):
                if not variant.strip():
                    errors.append(f"{key} variant {i}: empty")
                    continue
                wc = _word_count(variant)
                if wc < 30:
                    errors.append(f"{key} variant {i}: too short ({wc} words, min 30)")
                if wc > 400:
                    errors.append(f"{key} variant {i}: too long ({wc} words, max 400)")

    assert not errors, "Generation schema failures:\n" + "\n".join(errors)


@pytest.mark.asyncio
async def test_generation_no_banned_phrases(signal_scenarios):
    """Generated posts must not contain filler or brand-announcement phrases."""
    violations: list[str] = []

    for scenario in signal_scenarios:
        for gold_candidate in scenario.gold.candidates:
            summary, signal_type, context_summary, source_messages = _build_generation_inputs(
                scenario, gold_candidate
            )
            variants = await run_generate(
                summary=summary,
                signal_type=signal_type,
                context_summary=context_summary,
                variant_count=VARIANT_COUNT,
                source_messages=source_messages,
            )

            for i, variant in enumerate(variants):
                lower = variant.lower()
                for phrase in BANNED_PHRASES:
                    if phrase in lower:
                        violations.append(
                            f"{scenario.scenario_id} [{signal_type}] variant {i}: "
                            f"contains banned phrase '{phrase}'"
                        )

    if violations:
        print(f"\nBanned phrase violations ({len(violations)}):")
        for v in violations:
            print(f"  {v}")

    total_variants = sum(len(s.gold.candidates) * VARIANT_COUNT for s in signal_scenarios)
    assert len(violations) / max(total_variants, 1) <= 0.10, (
        f"{len(violations)}/{total_variants} variants contain banned phrases (threshold: 10%)"
    )


@pytest.mark.asyncio
async def test_generation_no_hashtags(signal_scenarios):
    """Generated posts must not contain hashtags."""
    violations: list[str] = []

    for scenario in signal_scenarios:
        for gold_candidate in scenario.gold.candidates:
            summary, signal_type, context_summary, source_messages = _build_generation_inputs(
                scenario, gold_candidate
            )
            variants = await run_generate(
                summary=summary,
                signal_type=signal_type,
                context_summary=context_summary,
                variant_count=VARIANT_COUNT,
                source_messages=source_messages,
            )

            for i, variant in enumerate(variants):
                hashtags = re.findall(r"(?<!\w)#\w+", variant)
                if hashtags:
                    violations.append(
                        f"{scenario.scenario_id} [{signal_type}] variant {i}: "
                        f"contains hashtags: {hashtags}"
                    )

    assert not violations, "Hashtag violations:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Layer 2: Structure compliance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generation_hook_structure(signal_scenarios):
    """Hook must stand alone (one line, ≤ 15 words) and post must have ≥ 3 sections."""
    failures: list[str] = []

    for scenario in signal_scenarios:
        for gold_candidate in scenario.gold.candidates:
            summary, signal_type, context_summary, source_messages = _build_generation_inputs(
                scenario, gold_candidate
            )
            variants = await run_generate(
                summary=summary,
                signal_type=signal_type,
                context_summary=context_summary,
                variant_count=VARIANT_COUNT,
                source_messages=source_messages,
            )

            for i, variant in enumerate(variants):
                paragraphs = _paragraphs(variant)
                key = f"{scenario.scenario_id} [{signal_type}] variant {i}"

                if not paragraphs:
                    failures.append(f"{key}: no paragraphs found")
                    continue

                hook = paragraphs[0]
                hook_lines = [line.strip() for line in hook.splitlines() if line.strip()]
                hook_words = _word_count(hook)

                if len(hook_lines) > 1:
                    failures.append(
                        f"{key}: hook has {len(hook_lines)} lines, must be exactly 1"
                    )
                if hook_words > 15:
                    failures.append(
                        f"{key}: hook is {hook_words} words (max 15): '{hook[:80]}'"
                    )
                if len(paragraphs) < 3:
                    failures.append(
                        f"{key}: only {len(paragraphs)} section(s) — "
                        "need hook + body + closing (minimum 3)"
                    )

    if failures:
        print(f"\nStructure failures ({len(failures)}):")
        for f in failures:
            print(f"  {f}")

    total_variants = sum(len(s.gold.candidates) * VARIANT_COUNT for s in signal_scenarios)
    assert len(failures) / max(total_variants, 1) <= 0.20, (
        f"{len(failures)}/{total_variants} variants fail structure checks (threshold: 20%)"
    )


@pytest.mark.asyncio
async def test_generation_contains_signal_details(signal_scenarios):
    """Each generated post must reference at least one concrete key fact from the signal."""
    failures: list[str] = []

    for scenario in signal_scenarios:
        for gold_candidate in scenario.gold.candidates:
            if not gold_candidate.summary_must_contain:
                continue

            summary, signal_type, context_summary, source_messages = _build_generation_inputs(
                scenario, gold_candidate
            )
            variants = await run_generate(
                summary=summary,
                signal_type=signal_type,
                context_summary=context_summary,
                variant_count=VARIANT_COUNT,
                source_messages=source_messages,
            )

            for i, variant in enumerate(variants):
                variant_norm = _normalize(variant)
                matched = any(
                    _normalize(fact) in variant_norm
                    for fact in gold_candidate.summary_must_contain
                )
                if not matched:
                    failures.append(
                        f"{scenario.scenario_id} [{signal_type}] variant {i}: "
                        f"no key facts found — expected one of: {gold_candidate.summary_must_contain}\n"
                        f"  post excerpt: {variant[:150]}"
                    )

    if failures:
        print(f"\nSignal detail misses ({len(failures)}):")
        for f in failures:
            print(f"  {f}")

    total_variants = sum(
        len(s.gold.candidates) * VARIANT_COUNT
        for s in signal_scenarios
        if any(c.summary_must_contain for c in s.gold.candidates)
    )
    assert len(failures) / max(total_variants, 1) <= 0.25, (
        f"{len(failures)}/{total_variants} variants missing signal details (threshold: 25%)"
    )


# ---------------------------------------------------------------------------
# Layer 3: LLM judge
# ---------------------------------------------------------------------------

@pytest.mark.llm_judge
@pytest.mark.skipif(not RUN_LLM_JUDGE, reason="Set EVAL_LLM_JUDGE=1 to run LLM judge evals")
@pytest.mark.asyncio
async def test_generation_quality_llm_judge(signal_scenarios):
    """Use GPT-4o-mini to score generated posts on hook strength, voice, and structure."""
    from pydantic import BaseModel

    from app.services.openai_client import get_openai_client

    class PostScore(BaseModel):
        hook_strength: int          # 1-5: attention-grabbing opener vs brand announcement
        voice_authenticity: int     # 1-5: real human / founder vs corporate press release
        structural_compliance: int  # 1-5: standalone hook + body paragraphs + standalone closing
        reasoning: str

    client = get_openai_client()
    scores: list[dict] = []

    for scenario in signal_scenarios:
        for gold_candidate in scenario.gold.candidates:
            summary, signal_type, context_summary, source_messages = _build_generation_inputs(
                scenario, gold_candidate
            )
            variants = await run_generate(
                summary=summary,
                signal_type=signal_type,
                context_summary=context_summary,
                variant_count=VARIANT_COUNT,
                source_messages=source_messages,
            )

            for i, variant in enumerate(variants):
                judge_response = await client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You evaluate LinkedIn posts written for B2B startup founders. "
                                "Be honest and critical — the goal is to identify weaknesses."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"LinkedIn post:\n\n{variant}\n\n"
                                "Score 1-5 for each dimension:\n"
                                "hook_strength: Is the opening line attention-grabbing? "
                                "Does it make you want to keep reading? "
                                "1=generic brand announcement, 5=compels reading\n"
                                "voice_authenticity: Does it sound like a real person "
                                "telling a story from their experience? "
                                "1=corporate press release, 5=genuinely human founder voice\n"
                                "structural_compliance: Does it have a standalone hook line, "
                                "body paragraphs separated by blank lines, and a standalone "
                                "closing sentence? 1=wall of text, 5=perfectly structured"
                            ),
                        },
                    ],
                    response_format=PostScore,
                    temperature=0,
                )
                score = judge_response.choices[0].message.parsed
                if score:
                    scores.append({
                        "scenario_id": scenario.scenario_id,
                        "signal_type": signal_type,
                        "variant": i,
                        "hook_strength": score.hook_strength,
                        "voice_authenticity": score.voice_authenticity,
                        "structural_compliance": score.structural_compliance,
                        "reasoning": score.reasoning,
                        "post": variant[:100],
                    })

    print("\n\nLLM Judge — Generation Quality")
    print("=" * 90)
    for s in scores:
        print(
            f"{s['scenario_id']} [{s['signal_type']}] v{s['variant']}  "
            f"hook={s['hook_strength']}/5 voice={s['voice_authenticity']}/5 "
            f"struct={s['structural_compliance']}/5"
        )
        print(f"  {s['post']}")
        print(f"  judge: {s['reasoning'][:80]}")

    if scores:
        avg_hook = sum(s["hook_strength"] for s in scores) / len(scores)
        avg_voice = sum(s["voice_authenticity"] for s in scores) / len(scores)
        avg_struct = sum(s["structural_compliance"] for s in scores) / len(scores)
        print(f"\nAverage hook strength:          {avg_hook:.2f}/5")
        print(f"Average voice authenticity:     {avg_voice:.2f}/5")
        print(f"Average structural compliance:  {avg_struct:.2f}/5")

        assert avg_hook >= 3.0, f"Average hook strength {avg_hook:.2f} is below 3.0"
        assert avg_voice >= 3.0, f"Average voice authenticity {avg_voice:.2f} is below 3.0"
        assert avg_struct >= 3.0, f"Average structural compliance {avg_struct:.2f} is below 3.0"
