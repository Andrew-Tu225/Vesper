"""
OpenAI async client factory.

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
    """Return a lazily-initialised AsyncOpenAI client."""
    global _client
    if _client is not None:
        return _client

    logger.info("LLM client: OpenAI")
    _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client
