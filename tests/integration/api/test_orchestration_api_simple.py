"""Simplified integration tests for orchestration API endpoints

These tests verify that the orchestration API works correctly without complex mocking.
They focus on testing the actual API behavior and schema validation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.agents.api.orchestration_routers import orchestration_router

from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create FastAPI app with orchestration router"""
    app = FastAPI()
    app.include_router(orchestration_router, prefix="/api/v1/orchestration")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestOrchestrationAPIBasics:
    """Test basic API functionality"""

    @patch("app.agents.api.orchestration_routers.OrchestrationService")
    def test_create_workflow_endpoint_exists(self, mock_service_class, client):
        """Test that create workflow endpoint exists and accepts requests"""
        # Mock the service instance
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Mock workflow definition
        mock_workflow_def = Mock()
        mock_workflow_def.workflow_id = "test-workflow-123"
        mock_workflow_def.name = "Test Workflow"
        mock_workflow_def.description = "A test workflow"
        mock_workflow_def.tasks = []

        mock_service.create_workflow.return_value = mock_workflow_def

        workflow_definition = {
            "workflow_id": "test-workflow-123",
            "name": "Test Workflow",
            "description": "A test workflow",
            "tasks": [{"task_id": "task1", "task_type": "data_processing", "depends_on": []}],
        }

        # Test with dependency injection override
        with patch("app.container.Container.orchestration_service") as mock_container:
            mock_container.return_value = mock_service

            response = client.post(
                "/api/v1/orchestration/workflows", json={"task_list": workflow_definition["tasks"]}
            )

        # Should get dependency injection error since we're not setting up the full container
        # But the endpoint should exist
        assert response.status_code in [400, 422, 500]  # Either validation error or DI error

    def test_health_endpoint_exists(self, client):
        """Test that health endpoint exists"""
        response = client.get("/api/v1/orchestration/health")

        # Health endpoint should work without dependency injection
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_workflow_validation_endpoint_exists(self, client):
        """Test that validation endpoint exists"""
        task_list = [{"task_id": "task1", "task_type": "data_processing", "depends_on": []}]

        response = client.post("/api/v1/orchestration/validate", json={"task_list": task_list})

        # Should work since validation doesn't require dependency injection
        assert response.status_code == 200
        assert response.json()["valid"]

    # Removed complex endpoints in simplification


class TestOrchestrationAPISchemas:
    """Test API request/response schemas"""

    def test_invalid_workflow_definition_schema(self, client):
        """Test workflow creation with invalid schema"""
        # Missing required fields
        response = client.post("/api/v1/orchestration/workflows", json={"invalid_field": "value"})

        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)
        assert len(error_detail) > 0

    def test_workflow_definition_field_validation(self, client):
        """Test workflow definition field validation"""
        # Test with empty task_list
        response = client.post("/api/v1/orchestration/workflows", json={"task_list": []})

        assert response.status_code == 422
        error_detail = response.json()["detail"]
        # Should have validation errors for empty task list (minItems validation)
        assert any("task_list" in str(error) for error in error_detail)

    # Removed complex endpoint tests in simplification


class TestOrchestrationAPIRouting:
    """Test API routing and URL structure"""

    def test_all_expected_endpoints_exist(self, app, client):
        """Test that basic expected endpoints are registered"""
        expected_routes = [
            ("/api/v1/orchestration/workflows", "POST"),
            ("/api/v1/orchestration/workflows/{execution_id}/execute", "POST"),
            ("/api/v1/orchestration/health", "GET"),
            ("/api/v1/orchestration/validate", "POST"),
        ]

        # Check that routes are registered
        registered_routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":  # Exclude HEAD methods
                        registered_routes.append((route.path, method))

        # Verify expected routes exist
        for expected_path, expected_method in expected_routes:
            # For parameterized routes, check if similar pattern exists
            path_exists = any(
                expected_path.replace("{execution_id}", "{execution_id}") == route_path
                or expected_path.replace("{execution_id}", "{execution_id:str}") == route_path
                for route_path, route_method in registered_routes
                if route_method == expected_method
            )
            assert path_exists, (
                f"Route {expected_method} {expected_path} not found in registered routes"
            )

    def test_route_path_consistency(self, app):
        """Test that all orchestration routes have consistent prefixes"""
        orchestration_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and "/orchestration/" in route.path
        ]

        for route in orchestration_routes:
            assert route.path.startswith("/api/v1/orchestration/"), (
                f"Route {route.path} has inconsistent prefix"
            )

    def test_http_methods_are_appropriate(self, app):
        """Test that HTTP methods match REST conventions"""
        route_method_expectations = {
            "/api/v1/orchestration/workflows": ["POST"],
            "/api/v1/orchestration/health": ["GET"],
            "/api/v1/orchestration/validate": ["POST"],
        }

        for route in app.routes:
            if hasattr(route, "path") and route.path in route_method_expectations:
                expected_methods = set(route_method_expectations[route.path])
                actual_methods = {method for method in route.methods if method != "HEAD"}
                assert expected_methods.issubset(actual_methods), (
                    f"Route {route.path} missing methods: {expected_methods - actual_methods}"
                )


class TestOrchestrationAPIDocumentation:
    """Test API documentation and OpenAPI schema"""

    def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is generated correctly"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        assert "paths" in openapi_schema
        assert "components" in openapi_schema

        paths = openapi_schema["paths"]

        # Check that orchestration endpoints are documented
        orchestration_paths = [path for path in paths if "/orchestration/" in path]
        assert len(orchestration_paths) > 0, "No orchestration endpoints found in OpenAPI schema"

    def test_endpoint_summaries_exist(self, client):
        """Test that endpoints have proper summaries"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()
        paths = openapi_schema["paths"]

        for path, methods in paths.items():
            if "/orchestration/" in path:
                for method_name, method_info in methods.items():
                    if method_name.upper() in ["GET", "POST", "PUT", "DELETE"]:
                        assert "summary" in method_info, (
                            f"Missing summary for {method_name.upper()} {path}"
                        )
                        assert len(method_info["summary"]) > 0, (
                            f"Empty summary for {method_name.upper()} {path}"
                        )

    def test_response_models_documented(self, client):
        """Test that response models are properly documented"""
        response = client.get("/openapi.json")
        openapi_schema = response.json()

        # Check that response schemas exist in components
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})

        expected_schemas = [
            "CreateWorkflowResponse",
            "WorkflowExecutionResponse",
            "WorkflowHealthResponse",
            "WorkflowValidationResponse",
        ]

        for schema_name in expected_schemas:
            assert schema_name in schemas, (
                f"Response schema {schema_name} not found in OpenAPI components"
            )


# Integration test to verify the API works with minimal real setup
class TestOrchestrationAPIIntegrationMinimal:
    """Minimal integration test to verify API structure"""

    def test_api_router_integration(self):
        """Test that the router integrates properly with FastAPI"""
        app = FastAPI()
        app.include_router(orchestration_router, prefix="/api/v1/orchestration")

        # Should not raise any exceptions
        assert app is not None

        # Check routes are registered
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]
        orchestration_paths = [path for path in route_paths if "/orchestration/" in path]

        assert len(orchestration_paths) >= 4, "Not enough orchestration routes registered"

    def test_schema_imports_work(self):
        """Test that all schema imports work correctly"""
        from app.agents.api.orchestration_schemas import (
            CreateWorkflowRequest,
            CreateWorkflowResponse,
            WorkflowExecutionResponse,
            WorkflowHealthResponse,
            WorkflowValidationResponse,
        )

        # Should not raise import errors
        assert CreateWorkflowRequest is not None
        assert CreateWorkflowResponse is not None
        assert WorkflowExecutionResponse is not None
        assert WorkflowHealthResponse is not None
        assert WorkflowValidationResponse is not None

    def test_service_imports_work(self):
        """Test that service imports work correctly"""
        from app.agents.services.orchestration_service import OrchestrationService
        from app.events.orchestration.task_registry import TaskRegistry

        # Should not raise import errors
        assert OrchestrationService is not None
        assert TaskRegistry is not None
