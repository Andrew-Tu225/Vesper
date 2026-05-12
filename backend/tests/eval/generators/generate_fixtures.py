"""
Generate synthetic Slack scenario fixtures for classifier eval.

The prompt strategy is "conversation-first, labels-second": the LLM writes
the team's actual Slack activity for a random workday, then determines what
signals (if any) emerged naturally. This produces realistic noise distribution
and avoids the trap of writing conversations designed to showcase a signal type.

Usage
-----
    # Generate 15 new scenarios and write to file
    python -m tests.eval.generators.generate_fixtures --count 15

    # Append to an existing file
    python -m tests.eval.generators.generate_fixtures --count 5 --append

    # Preview one scenario without saving
    python -m tests.eval.generators.generate_fixtures --count 1 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

OUTPUT_PATH = Path(__file__).parent.parent / "fixtures" / "scenarios.json"

# ---------------------------------------------------------------------------
# Company profiles — varied so scenarios don't all look the same
# ---------------------------------------------------------------------------

COMPANIES: list[dict[str, Any]] = [
    {
        "name": "Draftly",
        "description": "B2B content workflow tool, 8-person team. Helps marketing teams manage content pipelines from brief to publish.",
        "people": [
            ("U_james", "James", "CEO / co-founder"),
            ("U_sarah", "Sarah", "CTO / co-founder"),
            ("U_rachel", "Rachel", "Head of Product"),
            ("U_ben", "Ben", "Engineer"),
            ("U_lisa", "Lisa", "Engineer"),
            ("U_mike", "Mike", "Sales & BD"),
            ("U_jen", "Jen", "Designer"),
        ],
        "channels": ["C_general", "C_engineering", "C_product", "C_founders", "C_sales"],
    },
    {
        "name": "Pipestack",
        "description": "B2B sales automation, 10-person team. Helps SDR-heavy sales teams automate sequence management and follow-up timing.",
        "people": [
            ("U_omar", "Omar", "CEO"),
            ("U_alex", "Alex", "CTO"),
            ("U_priya", "Priya", "Engineer"),
            ("U_tom", "Tom", "Engineer"),
            ("U_nina", "Nina", "Head of Sales"),
            ("U_carlos", "Carlos", "Customer Success"),
            ("U_wei", "Wei", "Product"),
        ],
        "channels": ["C_general", "C_product", "C_engineering", "C_sales-wins"],
    },
    {
        "name": "Trackr",
        "description": "Project management SaaS for small teams, 6-person team. Aims to give teams the power of Jira without the complexity.",
        "people": [
            ("U_dan", "Dan", "CEO / founder"),
            ("U_kate", "Kate", "CTO / co-founder"),
            ("U_sam", "Sam", "Engineer"),
            ("U_zoe", "Zoe", "Designer"),
            ("U_maya", "Maya", "Product & Marketing"),
        ],
        "channels": ["C_general", "C_engineering", "C_company-updates", "C_product"],
    },
    {
        "name": "Flocal",
        "description": "Local business marketing platform, 9-person team. Helps brick-and-mortar businesses run loyalty programs and re-engagement campaigns.",
        "people": [
            ("U_dev", "Dev", "CEO / founder"),
            ("U_ana", "Ana", "CTO"),
            ("U_marco", "Marco", "Engineer"),
            ("U_jess", "Jess", "Engineer"),
            ("U_tara", "Tara", "Head of Partnerships"),
            ("U_raj", "Raj", "Customer Success"),
            ("U_ella", "Ella", "Designer"),
        ],
        "channels": ["C_general", "C_engineering", "C_growth", "C_product"],
    },
    {
        "name": "Openloop",
        "description": "API-first background check infrastructure, 7-person team. Helps HR tech platforms embed compliant background checks.",
        "people": [
            ("U_finn", "Finn", "CEO / founder"),
            ("U_lena", "Lena", "CTO"),
            ("U_chris", "Chris", "Engineer"),
            ("U_jade", "Jade", "Engineer"),
            ("U_nour", "Nour", "Head of Sales"),
            ("U_pablo", "Pablo", "Customer Success"),
        ],
        "channels": ["C_general", "C_engineering", "C_sales", "C_product"],
    },
]

# ---------------------------------------------------------------------------
# Pydantic models for structured LLM output
# ---------------------------------------------------------------------------

class GoldCandidate(BaseModel):
    source_ids: list[str]
    signal_type: str
    summary_must_contain: list[str] = Field(
        description="Key facts that should appear in a good classifier summary (customer name, metric, specific outcome)"
    )
    reason: str


class GoldLabels(BaseModel):
    candidates: list[GoldCandidate]
    embed_message_ids: list[str]


class ScenarioMessage(BaseModel):
    source_id: str
    channel_id: str
    user_id: str
    text: str
    thread_ts: str | None
    reaction_count: int


class GeneratedScenario(BaseModel):
    scenario_id: str
    description: str
    company_context: str
    messages: list[ScenarioMessage]
    gold: GoldLabels


# ---------------------------------------------------------------------------
# Generation prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are building a synthetic eval dataset for a Slack content classification system.

Your job: simulate ONE realistic block of startup team communication — about 4–6 hours \
of activity in one or more Slack channels. The output must be believable enough that \
a founder could look at it and say "yeah, that's basically what our Slack looks like."

## The critical rule
Write the conversation FIRST as if you are roleplaying the team's actual Slack. \
Then determine what content signals (if any) naturally emerged.

Do NOT write a conversation that is designed to demonstrate a particular signal type. \
Do NOT build messages around a label. Write the team doing their work, then check what \
signals that conversation happened to contain.

This constraint exists because the real signals in a startup's Slack are almost always \
incidental — a customer outcome dropped in the middle of a standup, a founder venting \
about something that turns into a reflection, a milestone noticed in passing. \
Artificial "this is our big customer win" messages are easy to classify and useless for eval.

## What realistic startup Slack looks like
- 40–60% of messages are pure noise: scheduling, PR review requests, quick questions, \
  logistics, "OOO until 3", "lmk", "on it", "👍"
- Short messages are normal: "🎉", "nice", "makes sense", "wait really?", "on it"
- People reference shared context that isn't in this scan: "remember that thing with Acme", \
  "from the call Tuesday", "the issue Sam flagged"
- Technical teams mix debugging, deploys, and product conversation in the same channel
- Casual grammar, abbreviations: "btw", "ngl", "tbh", "lol", contractions, some typos
- Significant moments often arrive quietly: "oh btw i just checked — we crossed 500 customers"
- Threads (thread_ts set to a parent source_id) let side conversations run parallel

## Signal types that might naturally emerge from the conversation
(These emerge from what the team is actually doing — do not engineer for them)

  customer_praise    — a specific customer expressed satisfaction with a concrete outcome or metric.
                       Generic internal "great job" does not count. Needs: who, what, outcome.

  product_win        — concrete milestone or measurable achievement. Needs a specific number or
                       outcome, not just "we made progress".

  launch_update      — something live, being shipped, or positioning being established for a
                       launch. Pre-launch discussions where the team articulates what the product
                       does and who it's for count — even if not shipped yet.

  hiring             — open role or team growth being actively decided, with enough substance
                       for a LinkedIn audience (not just "we might hire someone").

  founder_insight    — a founder or senior leader sharing a genuine personal reflection on
                       building the company. Must be substantive — not logistics or task talk.

## Output
- scenario_id: use the provided id
- description: one sentence describing what kind of scan window this is
- company_context: the company blurb from the input
- messages: 15–22 ScenarioMessage objects in chronological order
- gold: GoldLabels with candidates and embed_message_ids

For embed_message_ids: include all source_ids from candidates PLUS any other messages
that contain concrete, specific facts (named customers, metrics, decisions with rationale,
product specifics) that would help a copywriter understand the company's context in a month.
Exclude pure noise, logistics, and short acknowledgements."""


def _build_user_prompt(company: dict, scenario_id: str, message_count: int) -> str:
    people_lines = "\n".join(
        f"  {uid}: {name} ({role})"
        for uid, name, role in company["people"]
    )
    channels_line = ", ".join(company["channels"])

    return f"""\
Company: {company["name"]} — {company["description"]}

People:
{people_lines}

Channels available: {channels_line}

Generate scenario {scenario_id} with approximately {message_count} messages.
Pick 1–3 of the channels above for this scan window (not necessarily all of them).

Write the team's actual Slack for a random workday. Include plenty of noise. \
Let signals emerge naturally — or not at all. At least 2 of the 25 scenarios in this \
dataset should have zero signals, so it is completely fine if this one has none.

Return a single GeneratedScenario JSON object."""


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

async def generate_scenario(
    client: AsyncOpenAI,
    company: dict,
    scenario_id: str,
    model: str = "gpt-4o",
) -> GeneratedScenario:
    message_count = random.randint(15, 22)
    user_prompt = _build_user_prompt(company, scenario_id, message_count)

    response = await client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format=GeneratedScenario,
        temperature=0.9,
    )

    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError(f"LLM returned no parsed content for {scenario_id}")

    result.scenario_id = scenario_id
    return result


async def generate_batch(
    count: int,
    start_index: int,
    model: str = "gpt-4o",
) -> list[GeneratedScenario]:
    client = AsyncOpenAI()

    tasks = []
    for i in range(count):
        scenario_id = f"s{start_index + i:03d}"
        # Distribute evenly across companies, randomise within each run
        company = COMPANIES[(start_index + i) % len(COMPANIES)]
        tasks.append(generate_scenario(client, company, scenario_id, model))

    results = []
    for i, coro in enumerate(tasks):
        scenario_id = f"s{start_index + i:03d}"
        print(f"  Generating {scenario_id} ({COMPANIES[(start_index + i) % len(COMPANIES)]['name']})...", flush=True)
        try:
            scenario = await coro
            results.append(scenario)
            candidates_count = len(scenario.gold.candidates)
            types = [c.signal_type for c in scenario.gold.candidates]
            print(f"  ✓ {scenario_id}: {len(scenario.messages)} messages, {candidates_count} signal(s) {types}")
        except Exception as exc:
            print(f"  ✗ {scenario_id} failed: {exc}", file=sys.stderr)

    return results


def load_existing(path: Path) -> list[dict]:
    if path.exists():
        with path.open() as f:
            return json.load(f)
    return []


def save(scenarios: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(scenarios, f, indent=2)
    print(f"\nSaved {len(scenarios)} scenario(s) to {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic Slack eval scenarios")
    parser.add_argument("--count", type=int, default=5, help="Number of scenarios to generate")
    parser.add_argument("--append", action="store_true", help="Append to existing scenarios.json")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout, do not save")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output file path")
    args = parser.parse_args()

    output_path = Path(args.output)
    existing = load_existing(output_path) if args.append else []
    start_index = len(existing)

    print(f"Generating {args.count} scenario(s) starting at s{start_index:03d}...")
    new_scenarios = asyncio.run(generate_batch(args.count, start_index, args.model))

    as_dicts = [s.model_dump() for s in new_scenarios]

    if args.dry_run:
        print(json.dumps(as_dicts, indent=2))
        return

    all_scenarios = existing + as_dicts
    save(all_scenarios, output_path)

    signal_counts = [len(s["gold"]["candidates"]) for s in as_dicts]
    print(f"\nSummary: {len(new_scenarios)} scenarios, "
          f"{sum(signal_counts)} total signals, "
          f"{signal_counts.count(0)} noise-only")


if __name__ == "__main__":
    main()
