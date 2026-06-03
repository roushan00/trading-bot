import pytest
from httpx import ASGITransport, AsyncClient

from dashboard.api.main import app


@pytest.mark.asyncio
async def test_dashboard__health_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "paper"


@pytest.mark.asyncio
async def test_dashboard__index_returns_html() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "Trading Bot" in response.text
