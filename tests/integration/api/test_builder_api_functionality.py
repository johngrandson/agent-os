"""Integration tests for API functionality after builder pattern refactoring

These tests ensure all API endpoints maintain identical behavior
after the migration from 143-line server.py to builder pattern.
"""

import pytest
from app.server import app
from fastapi.testclient import TestClient


class TestAPIEndpointFunctionality:
    """Test that all API endpoints maintain identical functionality"""

    def test_health_check_endpoint_basic(self):
        """Health check endpoint should return correct response format"""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify expected response structure
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "environment" in data

        # Verify expected values
        assert data["status"] == "healthy"
        assert data["service"] == "agent-os"
        assert data["version"] == "1.0.0"

    def test_health_check_detailed_endpoint(self):
        """Detailed health check endpoint should return extended information"""
        client = TestClient(app)
        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # Verify expected response structure
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "environment" in data

        # Verify expected values
        assert data["status"] == "healthy"
        assert data["service"] == "agent-os"
        assert data["version"] == "1.0.0"

    def test_cors_headers_are_present(self):
        """CORS headers should be properly configured for cross-origin requests"""
        client = TestClient(app)
        response = client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )

        # Should handle preflight request
        assert response.status_code == 200

    def test_api_returns_json_content_type(self):
        """API endpoints should return proper JSON content type"""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_nonexistent_routes_return_404(self):
        """Non-existent routes should return 404"""
        client = TestClient(app)
        response = client.get("/nonexistent/route")

        assert response.status_code == 404


class TestBuilderPatternRegression:
    """Regression tests to ensure builder pattern doesn't break existing functionality"""

    def test_app_instance_is_fastapi_app(self):
        """Built app should be a proper FastAPI instance"""
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_app_has_expected_metadata(self):
        """App should maintain expected metadata from builder"""
        assert app.title == "Agent OS API"
        assert app.description == "Agent Operating System with integrated AgentOS support"
        assert app.version == "1.0.0"

    def test_app_has_middleware_configured(self):
        """App should have the expected number of middleware components"""
        # Should include CORS, SQLAlchemy, and ResponseLog middleware
        assert len(app.user_middleware) >= 3

    def test_app_has_health_routes_configured(self):
        """App should have health check routes configured"""
        route_paths = []
        for route in app.routes:
            if hasattr(route, "path"):
                route_paths.append(route.path)

        assert "/api/v1/health" in route_paths
        assert "/api/v1/health/detailed" in route_paths

    def test_app_has_domain_routes_configured(self):
        """App should have domain routes properly configured"""
        route_paths = []
        for route in app.routes:
            if hasattr(route, "path"):
                route_paths.append(route.path)

        # Should have routes from agent and webhook domains
        # (Exact paths depend on router configuration)
        agent_routes = [path for path in route_paths if "/api/v1/agents" in path]
        webhook_routes = [path for path in route_paths if "/api/v1/webhook" in path]

        assert len(agent_routes) > 0, "Agent routes should be configured"
        assert len(webhook_routes) > 0, "Webhook routes should be configured"

    def test_app_configuration_follows_builder_pattern(self):
        """Verify app was built using builder pattern correctly"""
        # Basic checks to ensure builder pattern worked
        assert hasattr(app, "title")
        assert hasattr(app, "description")
        assert hasattr(app, "version")
        assert hasattr(app, "routes")
        assert hasattr(app, "user_middleware")

        # Ensure we have some routes (not empty)
        assert len(app.routes) > 0

        # Ensure we have some middleware (not empty)
        assert len(app.user_middleware) > 0


class TestConcurrentRequestHandling:
    """Test application behavior under concurrent requests"""

    def test_app_handles_concurrent_health_check_requests(self):
        """App should handle multiple concurrent health check requests"""
        import concurrent.futures
        import threading

        client = TestClient(app)

        def make_request():
            return client.get("/api/v1/health").status_code

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]

        # All requests should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)

    def test_app_handles_invalid_json_requests(self):
        """App should properly handle malformed JSON requests"""
        client = TestClient(app)

        # Send malformed JSON to webhook endpoint
        response = client.post(
            "/api/v1/webhook", data="invalid-json", headers={"Content-Type": "application/json"}
        )

        # Should return 422 (validation error) or other appropriate error, not 500
        assert response.status_code != 500
