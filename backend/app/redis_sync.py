"""Synchronous Redis client for Celery workers.

FastAPI uses redis.asyncio (app/redis.py). Celery workers run in a sync
context and need the standard blocking redis.Redis client.

Usage
-----
    from app.redis_sync import get_sync_redis

    r = get_sync_redis()
    acquired = r.set("dedup:key", "1", nx=True, ex=86400)
"""

import os

import redis

_sync_redis: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    """Return the lazily-initialised synchronous Redis client.

    Reads REDIS_URL from the environment. decode_responses=True means all
    keys and values are returned as str rather than bytes.
    """
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.Redis.from_url(
            os.environ["REDIS_URL"], decode_responses=True
        )
    return _sync_redis
