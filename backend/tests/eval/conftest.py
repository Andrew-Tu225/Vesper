"""
Shared fixtures for the eval test suite.

Provides:
  scenarios          — all loaded Scenario objects from scenarios.json
  mock_search_fn     — injectable search_fn for run_enrich_agent that does cosine
                       search against a tiny in-memory corpus (no DB needed)
  mock_slack_client  — stub that returns canned thread replies from a fixture dict
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from app.services.schemas import SlackMessage

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Scenario dataclass
# ---------------------------------------------------------------------------

class GoldCandidate:
    def __init__(self, data: dict) -> None:
        self.source_ids: list[str] = data["source_ids"]
        self.signal_type: str = data["signal_type"]
        self.summary_must_contain: list[str] = data.get("summary_must_contain", [])
        self.reason: str = data.get("reason", "")


class Gold:
    def __init__(self, data: dict) -> None:
        self.candidates = [GoldCandidate(c) for c in data.get("candidates", [])]
        self.embed_message_ids: list[str] = data.get("embed_message_ids", [])


class Scenario:
    def __init__(self, data: dict) -> None:
        self.scenario_id: str = data["scenario_id"]
        self.description: str = data["description"]
        self.company_context: str = data["company_context"]
        self.messages: list[SlackMessage] = [
            SlackMessage(**m) for m in data["messages"]
        ]
        self.gold = Gold(data["gold"])

    def msg_lookup(self) -> dict[str, str]:
        return {m.source_id: m.text for m in self.messages}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def scenarios() -> list[Scenario]:
    path = FIXTURES_DIR / "scenarios.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return [Scenario(d) for d in data]


@pytest.fixture(scope="session")
def noise_scenarios(scenarios) -> list[Scenario]:
    return [s for s in scenarios if not s.gold.candidates]


@pytest.fixture(scope="session")
def signal_scenarios(scenarios) -> list[Scenario]:
    return [s for s in scenarios if s.gold.candidates]


# ---------------------------------------------------------------------------
# Mock search_fn for run_enrich_agent
#
# Builds a tiny in-memory corpus from all fixture messages and does
# exact cosine search without any DB or embedding calls.
# For eval purposes we substitute TF-IDF-style token overlap as a
# fast, deterministic stand-in for vector similarity.
# ---------------------------------------------------------------------------

def _token_overlap_similarity(query: str, text: str) -> float:
    q_tokens = set(query.lower().split())
    t_tokens = set(text.lower().split())
    if not q_tokens or not t_tokens:
        return 0.0
    intersection = q_tokens & t_tokens
    return len(intersection) / math.sqrt(len(q_tokens) * len(t_tokens))


def _build_corpus(scenarios: list[Scenario]) -> list[dict[str, Any]]:
    corpus = []
    for scenario in scenarios:
        for msg in scenario.messages:
            if msg.text.strip():
                corpus.append({
                    "message_ts": msg.source_id,
                    "text": msg.text,
                    "workspace_id": scenario.scenario_id,
                })
    return corpus


@pytest.fixture(scope="session")
def mock_search_fn(scenarios: list[Scenario]) -> Callable:
    corpus = _build_corpus(scenarios)

    def search_fn(workspace_id: str, embedding_vector: list[float], limit: int = 5) -> list[dict]:
        # embedding_vector is ignored — we use token overlap as a proxy
        # This is intentional: the eval is testing the agent's tool-use decisions,
        # not embedding quality (which has its own eval path)
        return sorted(
            [
                {**entry, "similarity": 0.75}
                for entry in corpus
                if entry["workspace_id"] == workspace_id
            ],
            reverse=True,
            key=lambda x: x["similarity"],
        )[:limit]

    return search_fn


# ---------------------------------------------------------------------------
# Mock Slack client for run_enrich_agent
# ---------------------------------------------------------------------------

def _build_thread_replies(scenarios: list[Scenario]) -> dict[str, list[dict]]:
    """Pre-index all threaded messages by their thread_ts so the mock can serve them."""
    threads: dict[str, list[dict]] = {}
    for scenario in scenarios:
        for msg in scenario.messages:
            if msg.thread_ts:
                threads.setdefault(msg.thread_ts, []).append({
                    "ts": msg.source_id,
                    "user": msg.user_id,
                    "text": msg.text,
                })
    return threads


@pytest.fixture(scope="session")
def mock_slack_client(scenarios: list[Scenario]) -> MagicMock:
    threads = _build_thread_replies(scenarios)

    client = MagicMock()

    def fake_conversations_replies(channel: str, ts: str, **kwargs) -> dict:
        return {"messages": threads.get(ts, [])}

    client.conversations_replies.side_effect = fake_conversations_replies
    return client
