"""
Embedding service — batch text embedding via OpenAI text-embedding-3-small.

All embedding calls in the application go through embed_texts. Keeping this
in one place means the model name and batching logic only live here.

Usage
-----
    from app.services.embedder import embed_texts

    embeddings = await embed_texts(["message one", "message two"])
    # embeddings[0] corresponds to "message one", embeddings[1] to "message two"
"""

from __future__ import annotations

import logging

from openai import APIError

from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"


class EmbedderError(Exception):
    """Raised when the OpenAI embeddings API call fails.

    Callers (Celery tasks) should catch this and trigger a task retry.
    """


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in a single API call.

    Returns embeddings in the same order as the input list.
    Returns an empty list if texts is empty (no API call made).

    Args:
        texts: Non-empty strings to embed. Callers should strip and filter
               empty strings before passing — the OpenAI API rejects them.

    Raises:
        EmbedderError: On API failure. Caller is responsible for retry.
    """
    if not texts:
        return []

    client = get_openai_client()
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
    except APIError as exc:
        raise EmbedderError(f"OpenAI embeddings API error: {exc}") from exc

    # response.data is ordered to match the input list
    embeddings = [item.embedding for item in response.data]

    logger.debug("embed_texts: embedded %d texts", len(embeddings))
    return embeddings
