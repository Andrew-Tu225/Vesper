"""Tests for the /health liveness + readiness endpoint."""

from unittest.mock import AsyncMock


async def test_health_returns_200_when_all_services_up(client, mock_db, mock_redis):
    resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["redis"] == "ok"


async def test_health_returns_503_when_db_is_down(client, mock_db, mock_redis):
    mock_db.execute = AsyncMock(side_effect=Exception("connection refused"))

    resp = await client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert "error" in body["checks"]["db"]
    assert body["checks"]["redis"] == "ok"


async def test_health_returns_503_when_redis_is_down(client, mock_db, mock_redis):
    mock_redis.ping = AsyncMock(side_effect=Exception("ECONNREFUSED"))

    resp = await client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"] == "ok"
    assert "error" in body["checks"]["redis"]


async def test_health_returns_503_when_both_services_are_down(client, mock_db, mock_redis):
    mock_db.execute = AsyncMock(side_effect=Exception("db down"))
    mock_redis.ping = AsyncMock(side_effect=Exception("redis down"))

    resp = await client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert "error" in body["checks"]["db"]
    assert "error" in body["checks"]["redis"]
