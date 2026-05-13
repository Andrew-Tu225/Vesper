"""
Classifier eval — three layers in order of cost:

  1. Schema invariants       free, always run — no LLM call
  2. Fixture-based metrics   no LLM call, compares against gold labels
  3. Summary quality         optional LLM judge (set EVAL_LLM_JUDGE=1)

Run fast checks only:
    pytest tests/eval/test_classifier_eval.py -m "not llm_judge"

Run everything including LLM judge:
    EVAL_LLM_JUDGE=1 pytest tests/eval/test_classifier_eval.py

The eval prints a per-scenario table and aggregate F1 at the end.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.services.classifier import batch_classify
from app.services.schemas import BatchClassifyResponse, ContentSignalCandidate

def _normalize(text: str) -> str:
    """Lowercase and strip comma separators in numbers (1,000 → 1000)."""
    return re.sub(r"(\d),(\d)", r"\1\2", text.lower())


VALID_SIGNAL_TYPES = {
    "customer_praise",
    "product_win",
    "launch_update",
    "hiring",
    "founder_insight",
}

RUN_LLM_JUDGE = os.getenv("EVAL_LLM_JUDGE", "0") == "1"


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    scenario_id: str
    description: str
    tp: int = 0   # gold candidate matched by a predicted candidate
    fp: int = 0   # predicted candidate with no matching gold
    fn: int = 0   # gold candidate with no matching prediction
    schema_errors: list[str] = field(default_factory=list)
    embed_recall: float = 0.0


def _match_candidates(
    predicted: list[ContentSignalCandidate],
    gold_candidates: list[Any],
) -> tuple[int, int, int]:
    """Match predicted vs gold candidates by signal_type + source_id overlap.

    A prediction matches a gold candidate if:
      1. signal_type is identical, AND
      2. At least one source_id overlaps between prediction and gold

    This is intentionally lenient on source_id set equality — a classifier
    that groups slightly differently but gets the type right is still useful.
    """
    matched_gold = set()
    matched_pred = set()

    for pi, pred in enumerate(predicted):
        for gi, gold in enumerate(gold_candidates):
            if gi in matched_gold:
                continue
            if pred.signal_type != gold.signal_type:
                continue
            pred_ids = set(pred.source_ids)
            gold_ids = set(gold.source_ids)
            if pred_ids & gold_ids:
                matched_gold.add(gi)
                matched_pred.add(pi)
                break

    tp = len(matched_gold)
    fp = len(predicted) - len(matched_pred)
    fn = len(gold_candidates) - len(matched_gold)
    return tp, fp, fn


def _embed_recall(
    predicted_embed_ids: list[str],
    gold_embed_ids: list[str],
) -> float:
    if not gold_embed_ids:
        return 1.0
    pred_set = set(predicted_embed_ids)
    gold_set = set(gold_embed_ids)
    return len(pred_set & gold_set) / len(gold_set)


# ---------------------------------------------------------------------------
# Layer 1: Schema invariants (no LLM call, always fast)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_schema_invariants(scenarios):
    """Classifier output must always respect schema constraints."""
    errors: list[str] = []

    for scenario in scenarios:
        result: BatchClassifyResponse = await batch_classify(scenario.messages)

        for candidate in result.candidates:
            if candidate.signal_type not in VALID_SIGNAL_TYPES:
                errors.append(
                    f"{scenario.scenario_id}: hallucinated signal_type={candidate.signal_type!r}"
                )
            if not candidate.source_ids:
                errors.append(f"{scenario.scenario_id}: candidate has empty source_ids")
            if not candidate.summary or len(candidate.summary.strip()) < 20:
                errors.append(
                    f"{scenario.scenario_id}: summary too short ({len(candidate.summary)} chars)"
                )

    assert not errors, "Schema invariant failures:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Layer 2: Fixture-based precision / recall
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_noise_rejection(noise_scenarios):
    """Scenarios with zero gold signals must produce zero candidates."""
    false_positives: list[str] = []

    for scenario in noise_scenarios:
        result: BatchClassifyResponse = await batch_classify(scenario.messages)
        if result.candidates:
            types = [c.signal_type for c in result.candidates]
            false_positives.append(
                f"{scenario.scenario_id} ({scenario.description}): "
                f"produced {len(result.candidates)} candidate(s): {types}"
            )

    assert not false_positives, (
        f"Classifier produced signals in {len(false_positives)} noise-only scenario(s):\n"
        + "\n".join(false_positives)
    )


@pytest.mark.asyncio
async def test_per_scenario_detection(scenarios):
    """Run classification on all scenarios and report precision/recall per scenario."""
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        response: BatchClassifyResponse = await batch_classify(scenario.messages)
        tp, fp, fn = _match_candidates(response.candidates, scenario.gold.candidates)
        recall = _embed_recall(response.embed_message_ids, scenario.gold.embed_message_ids)

        results.append(ScenarioResult(
            scenario_id=scenario.scenario_id,
            description=scenario.description[:60],
            tp=tp,
            fp=fp,
            fn=fn,
            embed_recall=recall,
        ))

    # Print results table
    print("\n\nClassifier Eval Results")
    print("=" * 90)
    print(f"{'ID':<8} {'TP':>4} {'FP':>4} {'FN':>4} {'Prec':>6} {'Recall':>8} {'EmbRec':>8}  Description")
    print("-" * 90)

    total_tp = total_fp = total_fn = 0
    embed_recalls = []

    for r in results:
        prec = r.tp / (r.tp + r.fp) if (r.tp + r.fp) > 0 else 1.0
        rec = r.tp / (r.tp + r.fn) if (r.tp + r.fn) > 0 else 1.0
        print(
            f"{r.scenario_id:<8} {r.tp:>4} {r.fp:>4} {r.fn:>4} "
            f"{prec:>6.2f} {rec:>8.2f} {r.embed_recall:>8.2f}  {r.description}"
        )
        total_tp += r.tp
        total_fp += r.fp
        total_fn += r.fn
        embed_recalls.append(r.embed_recall)

    print("-" * 90)
    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    f1 = (
        2 * overall_prec * overall_rec / (overall_prec + overall_rec)
        if (overall_prec + overall_rec) > 0
        else 0.0
    )
    avg_embed_recall = sum(embed_recalls) / len(embed_recalls) if embed_recalls else 0.0

    print(
        f"{'TOTAL':<8} {total_tp:>4} {total_fp:>4} {total_fn:>4} "
        f"{overall_prec:>6.2f} {overall_rec:>8.2f} {avg_embed_recall:>8.2f}"
    )
    print(f"\nF1: {f1:.3f}  |  Embed recall: {avg_embed_recall:.3f}")
    print()

    # Soft thresholds — these are alerts, not hard failures, for a seed set of 10
    assert overall_rec >= 0.60, (
        f"Signal recall {overall_rec:.2f} is below 0.60 — classifier is missing too many real signals"
    )
    assert overall_prec >= 0.60, (
        f"Precision {overall_prec:.2f} is below 0.60 — too many false positives in noise"
    )
    assert avg_embed_recall >= 0.50, (
        f"Embed recall {avg_embed_recall:.2f} is below 0.50 — "
        "important context messages not being flagged for storage"
    )


@pytest.mark.asyncio
async def test_summary_contains_key_facts(signal_scenarios):
    """For each correctly detected signal, the summary must mention key facts from gold."""
    failures: list[str] = []

    for scenario in signal_scenarios:
        response: BatchClassifyResponse = await batch_classify(scenario.messages)

        for gold_candidate in scenario.gold.candidates:
            # Find matching prediction
            match = None
            for pred in response.candidates:
                if pred.signal_type == gold_candidate.signal_type:
                    pred_ids = set(pred.source_ids)
                    gold_ids = set(gold_candidate.source_ids)
                    if pred_ids & gold_ids:
                        match = pred
                        break

            if match is None:
                continue  # not detected at all — already counted as FN in prior test

            summary_norm = _normalize(match.summary)
            missing_facts = [
                fact for fact in gold_candidate.summary_must_contain
                if _normalize(fact) not in summary_norm
            ]
            if missing_facts:
                failures.append(
                    f"{scenario.scenario_id} [{gold_candidate.signal_type}]: "
                    f"summary missing key facts: {missing_facts}\n"
                    f"  summary: {match.summary[:150]}"
                )

    if failures:
        print(f"\nSummary key-fact misses ({len(failures)}):")
        for f in failures:
            print(f"  {f}")

    # Allow up to 30% of signals to miss a key fact (LLMs paraphrase)
    total_signals = sum(len(s.gold.candidates) for s in signal_scenarios)
    assert len(failures) / max(total_signals, 1) <= 0.30, (
        f"{len(failures)}/{total_signals} summaries missing required key facts (threshold: 30%)"
    )


# ---------------------------------------------------------------------------
# Layer 3: LLM judge (optional, gated behind EVAL_LLM_JUDGE=1)
# ---------------------------------------------------------------------------

@pytest.mark.llm_judge
@pytest.mark.skipif(not RUN_LLM_JUDGE, reason="Set EVAL_LLM_JUDGE=1 to run LLM judge evals")
@pytest.mark.asyncio
async def test_summary_quality_llm_judge(signal_scenarios):
    """Use GPT-4o-mini to score each detected summary on specificity and utility."""
    from pydantic import BaseModel

    from app.services.openai_client import get_openai_client

    class SummaryScore(BaseModel):
        specificity: int  # 1-5: does it name outcomes, customers, metrics?
        utility: int      # 1-5: would a copywriter find this actionable?
        reasoning: str

    client = get_openai_client()
    scores: list[dict] = []

    for scenario in signal_scenarios:
        response: BatchClassifyResponse = await batch_classify(scenario.messages)

        for gold_candidate in scenario.gold.candidates:
            match = next(
                (
                    p for p in response.candidates
                    if p.signal_type == gold_candidate.signal_type
                    and set(p.source_ids) & set(gold_candidate.source_ids)
                ),
                None,
            )
            if match is None:
                continue

            source_texts = "\n".join(
                f"  [{sid}]: {t}"
                for m in scenario.messages
                for sid, t in [(m.source_id, m.text)]
                if sid in gold_candidate.source_ids
            )

            judge_response = await client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are evaluating summaries written by a content classifier. "
                            "Score the summary against the source messages."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Source messages:\n{source_texts}\n\n"
                            f"Summary: {match.summary}\n\n"
                            "Score 1-5:\n"
                            "specificity: Does the summary name specific details "
                            "(customer names, metrics, concrete outcomes)? "
                            "1=vague, 5=highly specific\n"
                            "utility: Would a copywriter find this summary actionable for "
                            "drafting a LinkedIn post? 1=useless, 5=everything they need"
                        ),
                    },
                ],
                response_format=SummaryScore,
                temperature=0,
            )
            score = judge_response.choices[0].message.parsed
            if score:
                scores.append({
                    "scenario_id": scenario.scenario_id,
                    "signal_type": gold_candidate.signal_type,
                    "specificity": score.specificity,
                    "utility": score.utility,
                    "reasoning": score.reasoning,
                    "summary": match.summary,
                })

    print("\n\nLLM Judge — Summary Quality")
    print("=" * 80)
    for s in scores:
        print(
            f"{s['scenario_id']} [{s['signal_type']}] "
            f"spec={s['specificity']}/5 util={s['utility']}/5"
        )
        print(f"  {s['summary'][:100]}")
        print(f"  judge: {s['reasoning'][:80]}")

    if scores:
        avg_spec = sum(s["specificity"] for s in scores) / len(scores)
        avg_util = sum(s["utility"] for s in scores) / len(scores)
        print(f"\nAverage specificity: {avg_spec:.2f}/5")
        print(f"Average utility:     {avg_util:.2f}/5")

        assert avg_spec >= 3.0, f"Average specificity {avg_spec:.2f} is below 3.0"
        assert avg_util >= 3.0, f"Average utility {avg_util:.2f} is below 3.0"
