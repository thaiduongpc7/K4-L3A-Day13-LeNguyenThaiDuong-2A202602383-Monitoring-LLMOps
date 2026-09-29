from __future__ import annotations

import asyncio

import httpx

from app.main import app


def test_middleware_generates_and_returns_correlation_id() -> None:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.get("/health")

    response = asyncio.run(send_request())

    correlation_id = response.headers["x-request-id"]
    assert correlation_id.startswith("req-")
    assert len(correlation_id) == 12
    int(correlation_id[4:], 16)
    assert int(response.headers["x-response-time-ms"]) >= 0
    assert response.json()["ok"] is True


def test_middleware_preserves_client_request_id() -> None:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.get(
                "/health", headers={"x-request-id": "req-client-01"}
            )

    response = asyncio.run(send_request())

    assert response.headers["x-request-id"] == "req-client-01"
