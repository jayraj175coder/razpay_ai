"""Tests for health and metadata endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root metadata endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "RecoverAI"
    assert "tagline" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["app_name"] == "RecoverAI"
    assert "timestamp" in data
    assert "llm_provider" in data
    assert "payment_provider" in data
