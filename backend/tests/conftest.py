"""Shared test fixtures for the Vesper backend test suite."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.database import get_db
from app.main import app
from app.redis import get_redis


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def override_deps(mock_redis: AsyncMock, mock_db: AsyncMock):
    """Override Redis and DB dependencies for all tests in the suite."""

    async def _redis():
        yield mock_redis

    async def _db():
        yield mock_db

    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_db] = _db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
