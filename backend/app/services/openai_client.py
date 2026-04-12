"""
OpenAI / OpenRouter async client factory.

Switching between OpenRouter (dev) and direct OpenAI (prod) is a config-only change:
- OpenRouter: set OPENROUTER_API_KEY and OPENROUTER_BASE_URL in .env
- Direct OpenAI: set OPENAI_API_KEY; leave OPENROUTER_API_KEY empty

When OPENROUTER_API_KEY is present it takes precedence.
Model name format differs per provider — configure MODEL_CLASSIFY and MODEL_GENERATE
in .env so no code change is needed when switching.

Usage
-----
    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    response = await client.beta.chat.completions.parse(
        model=settings.model_classify,
        response_format=SomeSchema,
        ...
    )
"""

from __future__ import annotations

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Return a lazily-initialised AsyncOpenAI client.

    Prefers OpenRouter when OPENROUTER_API_KEY is set.
    Falls back to direct OpenAI using OPENAI_API_KEY.
    """
    global _client
    if _client is not None:
        return _client

    if settings.openrouter_api_key:
        logger.info("LLM client: OpenRouter (%s)", settings.openrouter_base_url)
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    else:
        logger.info("LLM client: direct OpenAI")
        _client = AsyncOpenAI(api_key=settings.openai_api_key)

    return _client
