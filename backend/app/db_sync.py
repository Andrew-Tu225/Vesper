"""
Synchronous psycopg2 connection pool for Celery workers.

FastAPI uses async SQLAlchemy (asyncpg). Celery workers run in a sync context
and cannot use the async engine. This module provides a shared ThreadedConnectionPool
that worker tasks and sync services import when they need database access.

Usage
-----
    from app.db_sync import get_sync_pool

    pool = get_sync_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(...)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
"""

import os
from urllib.parse import urlparse, urlunparse

import psycopg2.pool

_db_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def make_sync_dsn() -> str:
    """Convert DATABASE_URL (asyncpg DSN) to a psycopg2-compatible DSN."""
    raw = os.environ["DATABASE_URL"]
    parsed = urlparse(raw)
    if parsed.scheme not in (
        "postgresql+asyncpg",
        "postgres+asyncpg",
        "postgresql",
        "postgres",
    ):
        raise ValueError(
            f"Unsupported DATABASE_URL scheme '{parsed.scheme}'. "
            "Expected postgresql+asyncpg:// or postgresql://"
        )
    sync_parsed = parsed._replace(scheme="postgresql")
    return urlunparse(sync_parsed)


def get_sync_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the lazily-initialised synchronous connection pool.

    Pool size of 2: workers run one task at a time (worker_prefetch_multiplier=1)
    so a single connection is almost always sufficient.
    """
    global _db_pool
    if _db_pool is None:
        _db_pool = psycopg2.pool.ThreadedConnectionPool(1, 2, dsn=make_sync_dsn())
    return _db_pool
