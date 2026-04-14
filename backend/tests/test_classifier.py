"""
Unit tests for services/classifier.py

All tests mock the OpenAI client — no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIError

from app.services.classifier import ClassifierError, batch_classify
from app.services.schemas import BatchClassifyResponse, ContentSignalCandidate, SlackMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_messages(*texts: str, channel_id: str = "C001") -> list[SlackMessage]:
    return [
        SlackMessage(
            source_id=f"17000000.00000{i}",
            channel_id=channel_id,
            user_id=f"U00{i}",
            text=text,
            reaction_count=0,
        )
        for i, text in enumerate(texts)
    ]


def _make_parse_response(
    candidates: list[ContentSignalCandidate],
    embed_message_ids: list[str] | None = None,
) -> MagicMock:
    """Build a mock response that mimics openai.beta.chat.completions.parse output."""
    parsed = BatchClassifyResponse(
        candidates=candidates,
        embed_message_ids=embed_message_ids or [],
    )
    choice = MagicMock()
    choice.message.parsed = parsed
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_classify_returns_worthy_candidates():
    """Happy path: worthy messages return candidates with correct fields."""
    messages = _make_messages(
        "Just got off a call with Acme — they love the new export feature!",
        "Totally, this is a great customer win",
    )
    expected_candidates = [
        ContentSignalCandidate(
            source_ids=["17000000.000000", "17000000.000001"],
            signal_type="customer_praise",
            summary="Acme praised the new export feature on a customer call.",
            reason="Direct customer praise with enthusiastic team reaction.",
        )
    ]
    mock_response = _make_parse_response(
        candidates=expected_candidates,
        embed_message_ids=["17000000.000000", "17000000.000001"],
    )

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await batch_classify(messages)

    assert isinstance(result, BatchClassifyResponse)
    assert len(result.candidates) == 1
    assert result.candidates[0].signal_type == "customer_praise"
    assert result.candidates[0].source_ids == ["17000000.000000", "17000000.000001"]
    assert "Acme" in result.candidates[0].summary


@pytest.mark.asyncio
async def test_batch_classify_filters_noise():
    """Noise messages are excluded — only worthy candidates returned."""
    messages = _make_messages(
        "standup at 10am tomorrow",            # noise
        "We just hit 1000 paying customers!",  # worthy
        "can someone review my PR?",           # noise
    )
    expected_candidates = [
        ContentSignalCandidate(
            source_ids=["17000000.000001"],
            signal_type="product_win",
            summary="The company reached 1000 paying customers.",
            reason="Major business milestone worth sharing externally.",
        )
    ]
    mock_response = _make_parse_response(
        candidates=expected_candidates,
        embed_message_ids=["17000000.000001"],
    )

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await batch_classify(messages)

    assert len(result.candidates) == 1
    assert result.candidates[0].signal_type == "product_win"
    assert result.candidates[0].source_ids == ["17000000.000001"]


@pytest.mark.asyncio
async def test_batch_classify_drops_unknown_signal_types():
    """Candidates with hallucinated signal_type values are silently dropped."""
    messages = _make_messages("Exciting news about our partnership!")
    bad_candidates = [
        ContentSignalCandidate(
            source_ids=["17000000.000000"],
            signal_type="unknown_type",  # not in SIGNAL_TYPES
            summary="Some partnership news.",
            reason="Sounds interesting.",
        )
    ]
    mock_response = _make_parse_response(
        candidates=bad_candidates,
        embed_message_ids=["17000000.000000"],
    )

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await batch_classify(messages)

    # candidate dropped — unknown signal_type
    assert result.candidates == []
    # embed_message_ids still passed through unchanged
    assert result.embed_message_ids == ["17000000.000000"]


@pytest.mark.asyncio
async def test_batch_classify_no_candidates_returns_empty_list():
    """LLM finds nothing post-worthy — candidates list is empty."""
    messages = _make_messages("standup at 10am", "sounds good", "brb")
    mock_response = _make_parse_response(candidates=[], embed_message_ids=[])

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await batch_classify(messages)

    assert result.candidates == []


# ---------------------------------------------------------------------------
# embed_message_ids
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_classify_returns_embed_message_ids():
    """embed_message_ids from the LLM response are passed through."""
    messages = _make_messages(
        "We hit 1000 users!",
        "sounds good",
        "working on the caching layer, got latency down to 40ms",
    )
    mock_response = _make_parse_response(
        candidates=[],
        embed_message_ids=["17000000.000000", "17000000.000002"],
    )

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await batch_classify(messages)

    assert result.embed_message_ids == ["17000000.000000", "17000000.000002"]


@pytest.mark.asyncio
async def test_batch_classify_candidate_source_ids_included_in_embed_ids():
    """When the LLM includes candidate source_ids in embed_message_ids, they are preserved."""
    messages = _make_messages(
        "Acme renewed their contract — biggest deal this quarter!",
        "amazing news",
    )
    candidate_ids = ["17000000.000000", "17000000.000001"]
    candidates = [
        ContentSignalCandidate(
            source_ids=candidate_ids,
            signal_type="customer_praise",
            summary="Acme renewed — biggest deal this quarter.",
            reason="Major customer renewal.",
        )
    ]
    # LLM correctly includes candidate source_ids in embed list
    mock_response = _make_parse_response(
        candidates=candidates,
        embed_message_ids=candidate_ids,
    )

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await batch_classify(messages)

    assert len(result.candidates) == 1
    for sid in result.candidates[0].source_ids:
        assert sid in result.embed_message_ids


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_classify_raises_classifier_error_on_api_failure():
    """API error from OpenAI propagates as ClassifierError."""
    messages = _make_messages("We shipped a new feature today!")

    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse = AsyncMock(
            side_effect=APIError("rate limit", request=MagicMock(), body=None)
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ClassifierError):
            await batch_classify(messages)


@pytest.mark.asyncio
async def test_batch_classify_empty_input_returns_empty_response():
    """Empty message list short-circuits without calling the API."""
    with patch("app.services.classifier.get_openai_client") as mock_get_client:
        result = await batch_classify([])

    assert isinstance(result, BatchClassifyResponse)
    assert result.candidates == []
    assert result.embed_message_ids == []
    mock_get_client.assert_not_called()
