"""
Tests for FastAPI application setup and health check.
These tests don't require Supabase — they validate the app boots correctly.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_openapi_docs(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "KudiCore API"

    def test_cors_headers(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should not return 405
        assert response.status_code in (200, 204, 400)


class TestRouteRegistration:
    """Verify all API route groups are registered."""

    def test_auth_routes_registered(self, client):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert any("/api/v1/auth" in p for p in paths)

    def test_transactions_routes_registered(self, client):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert any("/api/v1/transactions" in p for p in paths)

    def test_tax_routes_registered(self, client):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert any("/api/v1/tax" in p for p in paths)

    def test_chat_routes_registered(self, client):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert any("/api/v1/chat" in p for p in paths)

    def test_reports_routes_registered(self, client):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert any("/api/v1/reports" in p for p in paths)

    def test_billing_routes_registered(self, client):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert any("/api/v1/billing" in p for p in paths)


class TestUnauthenticatedAccess:
    """Verify protected routes reject unauthenticated requests."""

    def test_transactions_requires_auth(self, client):
        response = client.get("/api/v1/transactions/")
        assert response.status_code in (401, 403, 422)

    def test_tax_alerts_requires_auth(self, client):
        response = client.get("/api/v1/tax/alerts")
        assert response.status_code in (401, 403, 422)

    def test_chat_conversations_requires_auth(self, client):
        response = client.get("/api/v1/chat/conversations")
        assert response.status_code in (401, 403, 422)

    def test_reports_requires_auth(self, client):
        response = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "tax_summary", "year": 2025},
        )
        assert response.status_code in (401, 403, 422)

    def test_billing_subscription_requires_auth(self, client):
        response = client.get("/api/v1/billing/subscription")
        assert response.status_code in (401, 403, 422)


class TestTaxCalculationEndpoints:
    """Test tax calculation endpoints that don't require auth (public calculators)."""

    def test_pit_calculate_validation(self, client):
        # Missing required fields should return 422
        response = client.post("/api/v1/tax/pit/calculate", json={})
        assert response.status_code == 422

    def test_cit_calculate_validation(self, client):
        response = client.post("/api/v1/tax/cit/calculate", json={})
        assert response.status_code == 422

    def test_vat_calculate_validation(self, client):
        response = client.post("/api/v1/tax/vat/calculate", json={})
        assert response.status_code == 422

    def test_wht_calculate_validation(self, client):
        response = client.post("/api/v1/tax/wht/calculate", json={})
        assert response.status_code == 422
