"""API endpoint tests for router prefix correctness

These tests verify that generated API endpoints are accessible at the correct URLs
and demonstrate the pluralization issue in live API endpoints.
"""

import pytest
from scripts.generate_crud import get_table_name

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAPIRouterPrefixes:
    """Test API endpoints with correct router prefixes"""

    @pytest.fixture
    def mock_fastapi_app(self):
        """Create a mock FastAPI app for testing"""
        app = FastAPI()

        # Add a mock health endpoint
        @app.get("/api/v1/health")
        def health():
            return {"status": "healthy"}

        return app

    @pytest.fixture
    def test_client(self, mock_fastapi_app):
        """Create a test client"""
        return TestClient(mock_fastapi_app)

    def test_pluralization_fix_in_api_endpoints(self, mock_fastapi_app, test_client):
        """Test that verifies the pluralization fix works correctly in API endpoints

        This test shows that endpoints now use correct pluralization.
        """
        entity_name = "test_entity"

        # What the fixed implementation produces (correct)
        current_correct_plural = get_table_name(entity_name)  # Now returns "test_entities"
        correct_prefix = f"/api/v1/{current_correct_plural}"

        # What it should produce (same as above after fix)
        expected_plural = "test_entities"
        expected_prefix = f"/api/v1/{expected_plural}"

        # Simulate adding a router with correct pluralization (after fix)
        @mock_fastapi_app.get(f"{correct_prefix}")
        def get_correct_endpoint():
            return {"entities": [], "note": "correct pluralization"}

        # Test that correct URL is accessible
        correct_response = test_client.get(correct_prefix)
        assert correct_response.status_code == 200
        assert "correct pluralization" in correct_response.json()["note"]

        # Verify the fix: current implementation now produces correct plural
        assert current_correct_plural == "test_entities", (
            f"Fixed implementation should produce correct plural: {current_correct_plural}"
        )

        # This assertion shows we get what we want
        assert expected_plural == "test_entities", f"Expected correct plural: {expected_plural}"

        # The URLs are now the same, showing the fix works
        assert correct_prefix == expected_prefix, (
            f"Fixed implementation creates correct URL '{correct_prefix}' "
            f"matching expected '{expected_prefix}'"
        )

    @pytest.mark.parametrize(
        "entity_name,expected_plural,current_wrong",
        [
            ("test_entity", "test_entities", "test_entitys"),
            ("user_profile", "user_profiles", "user_profiles"),  # Might work
            ("order_item", "order_items", "order_items"),  # Might work
            ("company", "companies", "companys"),
            ("category", "categories", "categorys"),
            ("data_source", "data_sources", "data_sources"),  # Might work
            ("payment_method", "payment_methods", "payment_methods"),  # Might work
        ],
    )
    def test_api_endpoint_accessibility(
        self, entity_name, expected_plural, current_wrong, mock_fastapi_app, test_client
    ):
        """Test that API endpoints are accessible at correct URLs

        Args:
            entity_name: The entity name to test
            expected_plural: The correct plural form
            current_wrong: What current implementation produces
        """
        # Get what the current implementation would produce
        actual_plural = get_table_name(entity_name)
        actual_url = f"/api/v1/{actual_plural}"
        expected_url = f"/api/v1/{expected_plural}"

        # Add endpoint with current implementation
        @mock_fastapi_app.get(f"{actual_url}")
        def get_current_implementation():
            return {"entity": entity_name, "plural": actual_plural}

        # Test accessibility
        response = test_client.get(actual_url)
        assert response.status_code == 200

        data = response.json()
        assert data["entity"] == entity_name

        # Document the bug: when actual != expected, we have wrong URLs
        if actual_plural != expected_plural:
            # This should fail, demonstrating the API endpoint bug
            assert actual_url == expected_url, (
                f"API endpoint for '{entity_name}' is accessible at wrong URL: "
                f"'{actual_url}' instead of correct '{expected_url}'"
            )


class TestAPIEndpointGeneration:
    """Test complete API endpoint generation with router prefixes"""

    def test_generated_crud_endpoints_accessibility(self):
        """Test that all CRUD endpoints are accessible at correct URLs"""
        entity_name = "test_entity"
        entity_plural = get_table_name(entity_name)
        base_url = f"/api/v1/{entity_plural}"

        # Expected CRUD endpoints
        expected_endpoints = [
            ("GET", f"{base_url}"),  # List entities
            ("POST", f"{base_url}"),  # Create entity
            ("GET", f"{base_url}/{{entity_id}}"),  # Get entity by ID
            ("PUT", f"{base_url}/{{entity_id}}"),  # Update entity
            ("DELETE", f"{base_url}/{{entity_id}}"),  # Delete entity
        ]

        app = FastAPI()

        # Mock the generated router endpoints
        for method, url_pattern in expected_endpoints:
            if method == "GET" and "{entity_id}" not in url_pattern:

                @app.get(url_pattern)
                def list_entities():
                    return {"entities": []}
            elif method == "POST":

                @app.post(url_pattern, status_code=201)
                def create_entity():
                    return {"id": "123", "name": "test"}
            elif method == "GET" and "{entity_id}" in url_pattern:

                @app.get(url_pattern.replace("{entity_id}", "{entity_id:str}"))
                def get_entity(entity_id: str):
                    return {"id": entity_id, "name": "test"}
            elif method == "PUT":

                @app.put(url_pattern.replace("{entity_id}", "{entity_id:str}"))
                def update_entity(entity_id: str):
                    return {"id": entity_id, "name": "updated"}
            elif method == "DELETE":

                @app.delete(url_pattern.replace("{entity_id}", "{entity_id:str}"), status_code=204)
                def delete_entity(entity_id: str):
                    return

        client = TestClient(app)

        # Test each endpoint
        # List entities
        response = client.get(f"{base_url}")
        assert response.status_code == 200

        # Create entity
        response = client.post(f"{base_url}", json={"name": "test"})
        assert response.status_code == 201

        # Get entity by ID
        response = client.get(f"{base_url}/123")
        assert response.status_code == 200

        # Update entity
        response = client.put(f"{base_url}/123", json={"name": "updated"})
        assert response.status_code == 200

        # Delete entity
        response = client.delete(f"{base_url}/123")
        assert response.status_code == 204

        # The problem: all these endpoints are at wrong URLs due to pluralization bug
        expected_correct_base = "/api/v1/test_entities"
        actual_base = f"/api/v1/{entity_plural}"

        # This assertion should fail, showing the API URL bug
        assert actual_base == expected_correct_base, (
            f"All CRUD endpoints are at wrong base URL '{actual_base}' "
            f"instead of correct '{expected_correct_base}'"
        )

    def test_api_documentation_correctness(self):
        """Test that API documentation shows correct endpoint URLs

        This test ensures that OpenAPI/Swagger docs display the right URLs
        """
        entity_name = "test_entity"
        entity_plural = get_table_name(entity_name)

        app = FastAPI(title="Test API", description="API with potentially wrong pluralization")

        # Add a test endpoint
        @app.get(f"/api/v1/{entity_plural}")
        def list_test_entities():
            """List all test entities"""
            return {"entities": []}

        client = TestClient(app)

        # Get OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema.get("paths", {})

        # Check if the endpoint is documented with wrong URL
        wrong_path = f"/api/v1/{entity_plural}"
        correct_path = "/api/v1/test_entities"

        assert wrong_path in paths, f"API docs should contain endpoint at {wrong_path}"

        # This should fail, showing documentation URL bug
        if wrong_path != correct_path:
            assert correct_path in paths, (
                f"API documentation shows wrong endpoint URL '{wrong_path}' "
                f"instead of correct '{correct_path}'"
            )

    def test_client_sdk_generation_urls(self):
        """Test that client SDK generation uses correct URLs

        This simulates how API clients/SDKs would be affected by wrong URLs
        """
        entity_name = "test_entity"
        wrong_plural = get_table_name(entity_name)  # "test_entitys"
        correct_plural = "test_entities"

        # Simulate client SDK URL generation
        class APIClient:
            def __init__(self, base_url: str):
                self.base_url = base_url

            def get_entities_url(self, entity_plural: str) -> str:
                return f"{self.base_url}/api/v1/{entity_plural}"

        client = APIClient("https://api.example.com")

        # What current implementation would generate
        wrong_url = client.get_entities_url(wrong_plural)
        correct_url = client.get_entities_url(correct_plural)

        # This should fail, showing client SDK URL bug
        assert wrong_url == correct_url, (
            f"Client SDK would generate wrong URL '{wrong_url}' instead of correct '{correct_url}'"
        )


class TestAPIConsistencyAcrossEndpoints:
    """Test that pluralization is consistent across all API endpoints"""

    def test_list_endpoint_url_consistency(self):
        """Test that list endpoints use consistent pluralization"""
        entities = ["user", "product", "test_entity", "user_profile", "company"]

        for entity_name in entities:
            plural = get_table_name(entity_name)
            list_url = f"/api/v1/{plural}"

            # All list endpoints should follow same pattern
            assert list_url.startswith("/api/v1/"), f"Invalid list URL format: {list_url}"
            assert list_url.endswith("s"), f"List URL should end with 's': {list_url}"

            # Check for specific compound word issues
            if "_" in entity_name:
                # Compound words should have proper pluralization
                assert not list_url.endswith("_entitys"), (
                    f"Compound word '{entity_name}' should not end with '_entitys' "
                    f"in URL: {list_url}"
                )

    def test_detail_endpoint_url_consistency(self):
        """Test that detail endpoints (GET/PUT/DELETE by ID) use consistent URLs"""
        entity_name = "test_entity"
        plural = get_table_name(entity_name)
        detail_url_pattern = f"/api/v1/{plural}/{{entity_id}}"

        # Detail URLs should use plural form consistently
        expected_pattern = "/api/v1/test_entities/{entity_id}"

        # This should fail, showing detail endpoint URL bug
        assert detail_url_pattern == expected_pattern, (
            f"Detail endpoint URL pattern '{detail_url_pattern}' should be '{expected_pattern}'"
        )

    def test_nested_resource_url_consistency(self):
        """Test nested resource URLs for compound entities"""
        # Example: /api/v1/user_profiles/123/settings
        parent_entity = "user_profile"
        parent_plural = get_table_name(parent_entity)
        nested_url = f"/api/v1/{parent_plural}/123/settings"

        expected_url = "/api/v1/user_profiles/123/settings"

        # This should pass for some cases, fail for others
        assert nested_url == expected_url, (
            f"Nested resource URL '{nested_url}' should be '{expected_url}'"
        )


@pytest.fixture
def sample_crud_app():
    """Create a sample app with CRUD endpoints for testing"""
    app = FastAPI()

    @app.get("/api/v1/test_entitys")  # Wrong pluralization
    def list_entities_wrong():
        return {"entities": [], "note": "wrong_plural"}

    @app.get("/api/v1/test_entities")  # Correct pluralization
    def list_entities_correct():
        return {"entities": [], "note": "correct_plural"}

    return app


class TestRealWorldAPIUsage:
    """Test real-world API usage scenarios"""

    def test_api_client_expectations(self, sample_crud_app):
        """Test what API clients would expect vs what they get"""
        client = TestClient(sample_crud_app)

        # What API clients would naturally expect
        expected_url = "/api/v1/test_entities"
        response = client.get(expected_url)
        assert response.status_code == 200
        assert response.json()["note"] == "correct_plural"

        # What the buggy implementation produces
        wrong_url = "/api/v1/test_entitys"
        response = client.get(wrong_url)
        assert response.status_code == 200
        assert response.json()["note"] == "wrong_plural"

        # The problem: clients have to use wrong URLs
        assert expected_url != wrong_url, (
            f"Clients expect '{expected_url}' but may get '{wrong_url}'"
        )

    def test_api_versioning_with_pluralization_bug(self):
        """Test how pluralization bug affects API versioning"""
        entity_name = "test_entity"
        wrong_plural = get_table_name(entity_name)

        # URLs across different API versions
        v1_url = f"/api/v1/{wrong_plural}"
        v2_url = f"/api/v2/{wrong_plural}"  # Bug propagates to new versions

        expected_v1_url = "/api/v1/test_entities"
        expected_v2_url = "/api/v2/test_entities"

        # Both versions have wrong URLs due to the bug
        assert v1_url == expected_v1_url, f"v1 URL wrong: {v1_url} != {expected_v1_url}"
        assert v2_url == expected_v2_url, f"v2 URL wrong: {v2_url} != {expected_v2_url}"
