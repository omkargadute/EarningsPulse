"""Backend API tests."""

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "EarningsPulse API"
    assert "health" in data


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "EarningsPulse API"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_check(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["api"] is True
    assert "prism_required" in data["checks"]


@pytest.mark.asyncio
async def test_readiness_fails_when_prism_required_but_missing():
    from app.api.deps import get_app_settings
    from app.config import Settings

    settings = Settings(
        prism_required=True,
        prism_api_key=None,
        prism_project_id=None,
    )
    app.dependency_overrides[get_app_settings] = lambda: settings
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/ready")
    finally:
        app.dependency_overrides.pop(get_app_settings, None)

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["prism_required"] is True
    assert data["checks"]["prism_enabled"] is False
