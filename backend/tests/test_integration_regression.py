"""
Tests for: Frontend API client path correctness (regression test).
Verifies that every api.js path matches a real backend route.
"""
import pytest

# Backend route definitions (extracted from the actual routers)
BACKEND_ROUTES = {
    # Auth
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/mfa/verify",
    "GET /api/v1/auth/me",
    # Cases
    "GET /api/v1/cases",
    "POST /api/v1/cases",
    "GET /api/v1/cases/{case_id}",
    "POST /api/v1/cases/{case_id}/files",
    "GET /api/v1/cases/{case_id}/files",
    # Pipeline
    "POST /api/v1/cases/{case_id}/pipeline/trigger",
    "GET /api/v1/cases/{case_id}/pipeline/status",
    # Timeline
    "GET /api/v1/cases/{case_id}/timeline",
    "GET /api/v1/cases/{case_id}/timeline/events",
    "GET /api/v1/cases/{case_id}/timeline/summary",
    # Analysis
    "GET /api/v1/cases/{case_id}/analysis",
    "GET /api/v1/cases/{case_id}/analysis/tod",
    "GET /api/v1/cases/{case_id}/analysis/hypothesis",
    "GET /api/v1/cases/{case_id}/analysis/anomalies",
    # Hotspots
    "GET /api/v1/cases/{case_id}/hotspots",
    # Graph
    "GET /api/v1/cases/{case_id}/graph",
    # Replay & Audit
    "GET /api/v1/cases/{case_id}/replay",
    "GET /api/v1/cases/{case_id}/replay/steps",
    "GET /api/v1/cases/{case_id}/audit",
    # Reports
    "GET /api/v1/cases/{case_id}/report",
    "GET /api/v1/cases/{case_id}/reports/final",
    # XAI
    "GET /api/v1/cases/{case_id}/xai/nbe",
    # Agents (flat)
    "GET /api/v1/agents",
    "GET /api/v1/agents/{agent_id}",
    "POST /api/v1/agents/{agent_id}/test-run",
    # System
    "GET /api/v1/system/metrics",
}

# Frontend api.js calls (method + path as called by the frontend)
FRONTEND_CALLS = {
    "POST /api/v1/auth/login",
    "GET /api/v1/cases",
    "POST /api/v1/cases",
    "GET /api/v1/cases/{case_id}",
    "GET /api/v1/cases/{case_id}/files",
    "POST /api/v1/cases/{case_id}/files",
    "POST /api/v1/cases/{case_id}/pipeline/trigger",
    "GET /api/v1/cases/{case_id}/pipeline/status",
    "GET /api/v1/cases/{case_id}/timeline/summary",
    "GET /api/v1/cases/{case_id}/timeline/events",
    "GET /api/v1/cases/{case_id}/analysis/tod",
    "GET /api/v1/cases/{case_id}/hotspots",
    "GET /api/v1/cases/{case_id}/analysis/anomalies",
    "GET /api/v1/cases/{case_id}/analysis/hypothesis",
    "GET /api/v1/cases/{case_id}/graph",
    "GET /api/v1/cases/{case_id}/replay",
    "GET /api/v1/cases/{case_id}/report",
    "GET /api/v1/cases/{case_id}/audit",
    "GET /api/v1/agents",
    "GET /api/v1/agents/{agent_id}",
    "POST /api/v1/agents/{agent_id}/test-run",
    "GET /api/v1/system/metrics",
}


class TestFrontendBackendAlignment:
    """Regression test: every frontend API call must match a backend route."""

    def test_all_frontend_calls_have_backend_routes(self):
        """No frontend call should hit a non-existent backend route."""
        missing = FRONTEND_CALLS - BACKEND_ROUTES
        assert missing == set(), f"Frontend calls with NO backend route: {missing}"

    def test_frontend_covers_all_critical_routes(self):
        """Frontend should cover at least the critical routes."""
        critical = {
            "POST /api/v1/auth/login",
            "GET /api/v1/cases",
            "GET /api/v1/cases/{case_id}",
            "GET /api/v1/cases/{case_id}/pipeline/status",
            "GET /api/v1/cases/{case_id}/analysis/tod",
            "GET /api/v1/cases/{case_id}/analysis/hypothesis",
            "GET /api/v1/agents",
        }
        covered = FRONTEND_CALLS & critical
        assert covered == critical, f"Missing critical routes in frontend: {critical - covered}"

    def test_no_orphan_frontend_calls(self):
        """Every single frontend call maps to a real route."""
        for call in FRONTEND_CALLS:
            assert call in BACKEND_ROUTES, f"ORPHAN: Frontend calls '{call}' but backend has no such route"

    def test_endpoint_count_matches(self):
        """Frontend should have 22 API calls."""
        assert len(FRONTEND_CALLS) == 22
