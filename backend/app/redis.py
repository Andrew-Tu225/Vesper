from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.config import settings

_pool: Redis | None = None


def get_redis_pool() -> Redis:
    global _pool
    if _pool is None:
        _pool = Redis.from_url(settings.redis_url, decode_responses=True)
    return _pool


async def close_redis_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    redis = get_redis_pool()
    yield redis
