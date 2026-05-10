"""
Tests for: api/ endpoints — Route registration, response schemas, CORS, auth.
Uses FastAPI's TestClient (no real DB/Redis needed).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════
# Mock all external dependencies before importing app
# ═══════════════════════════════════════════════════════════

# Mock core modules so main.py doesn't try to connect to real services
mock_db = MagicMock()
mock_db.get_pool = AsyncMock()
mock_db.close_pool = AsyncMock()
mock_db.fetchrow = AsyncMock(return_value=None)
mock_db.fetch = AsyncMock(return_value=[])
mock_db.fetchval = AsyncMock(return_value=0)
mock_db.execute = AsyncMock()

mock_storage = MagicMock()
mock_storage.get_minio = MagicMock()

mock_redis_close = AsyncMock()

with patch.dict("sys.modules", {
    "core.database": MagicMock(db=mock_db),
    "core.storage": MagicMock(storage=mock_storage),
    "core.redis_client": MagicMock(close_redis=mock_redis_close, publish_task=AsyncMock()),
    "core.config": MagicMock(settings=MagicMock(
        JWT_SECRET="test-secret-key",
        JWT_ALGORITHM="HS256",
        JWT_EXPIRE_MINUTES=60,
    )),
    "core.llm_gateway": MagicMock(llm=MagicMock()),
    "agents.base": MagicMock(BaseAgent=type("BaseAgent", (), {})),
}):
    from main import app

client = TestClient(app)


class TestHealthCheck:
    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "evidra-api"


class TestRouteRegistration:
    """Verify all API routes are registered and reachable."""

    def test_auth_login_route_exists(self):
        response = client.post("/api/v1/auth/login", data={"username": "test", "password": "test"})
        # Should return 400 (bad creds) not 404 (not found)
        assert response.status_code != 404

    def test_cases_route_exists(self):
        response = client.get("/api/v1/cases")
        # Will return 401 (no auth) not 404
        assert response.status_code in [401, 200, 422]

    def test_agents_route_exists(self):
        response = client.get("/api/v1/agents")
        assert response.status_code == 200

    def test_system_metrics_exists(self):
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200


class TestAgentsEndpoint:
    """Test the agents registry endpoint (no auth required)."""

    def test_returns_17_agents(self):
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) == 17

    def test_agent_has_required_fields(self):
        response = client.get("/api/v1/agents")
        agents = response.json()
        for agent in agents:
            assert "id" in agent
            assert "name" in agent
            assert "tier" in agent
            assert "category" in agent
            assert "model" in agent

    def test_tiers_range_0_to_7(self):
        response = client.get("/api/v1/agents")
        agents = response.json()
        tiers = set(a["tier"] for a in agents)
        for t in range(8):
            assert t in tiers

    def test_get_single_agent(self):
        response = client.get("/api/v1/agents/tod_agent")
        assert response.status_code == 200
        agent = response.json()
        assert agent["id"] == "tod_agent"
        assert agent["tier"] == 3

    def test_get_nonexistent_agent_404(self):
        response = client.get("/api/v1/agents/nonexistent_agent")
        assert response.status_code == 404


class TestSystemMetrics:
    """Test the system metrics endpoint."""

    def test_returns_expected_fields(self):
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "active_pipelines" in data
        assert "system_health" in data
        assert "agents_total" in data
        assert data["agents_total"] == 17

    def test_system_health_is_healthy(self):
        response = client.get("/api/v1/system/metrics")
        data = response.json()
        assert data["system_health"] == "HEALTHY"


class TestCORSHeaders:
    """Test CORS middleware is correctly configured."""

    def test_cors_allows_all_origins(self):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.headers.get("access-control-allow-origin") in ["*", "http://localhost:3000"]
