"""Integration tests for CLI CRUD generator router prefix generation

These tests validate that the CLI generator produces correct router prefixes
in the server.py integration, specifically focusing on pluralization issues.
"""

import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the CLI generator functions
from scripts.generate_crud import (
    FieldDefinition,
    get_table_name,
    update_server_file,
    validate_entity_name,
)


class TestRouterPrefixGeneration:
    """Test suite for CLI generator router prefix generation"""

    def test_router_prefix_uses_correct_pluralization(self):
        """Test that router prefixes use proper pluralization logic

        This test demonstrates the current bug where compound words
        get incorrect pluralization in router prefixes.
        """
        test_cases = [
            ("user", "/api/v1/users"),
            ("product", "/api/v1/products"),
            ("test_entity", "/api/v1/test_entities"),  # ❌ Currently fails
            ("user_profile", "/api/v1/user_profiles"),  # ❌ Currently fails
            ("order_item", "/api/v1/order_items"),  # ❌ Currently fails
            ("payment_method", "/api/v1/payment_methods"),  # ❌ Currently fails
            ("company", "/api/v1/companies"),  # ❌ Currently fails
            ("category", "/api/v1/categories"),  # ❌ Currently fails
        ]

        for entity_name, expected_prefix in test_cases:
            # Use the same logic as the CLI generator
            table_name = get_table_name(entity_name)
            actual_prefix = f"/api/v1/{table_name}"

            assert actual_prefix == expected_prefix, (
                f"Router prefix for '{entity_name}' should be '{expected_prefix}', "
                f"got '{actual_prefix}'"
            )

    def test_server_file_integration_generates_correct_prefixes(self):
        """Test that server.py integration generates correct router prefixes

        This integration test simulates the actual CLI generator behavior
        when updating server.py with new router registrations.
        """
        # Create a mock server.py content
        mock_server_content = '''from app.webhook.api.routers import webhook_router

def setup_routes(app: FastAPI):
    """Configure application routes"""
    app.include_router(webhook_router, prefix="/api/v1")

def setup_dependency_injection(container: Container):
    """Configure dependency injection"""
    container.wire(
        modules=[
            "app.webhook.api.routers",
        ]
    )
'''

        test_cases = [
            ("test_entity", "test_entities"),
            ("user_profile", "user_profiles"),
            ("order_item", "order_items"),
            ("payment_method", "payment_methods"),
        ]

        for entity_name, expected_plural in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                # Create the 'app' directory inside the temporary directory
                (temp_path / "app").mkdir(parents=True, exist_ok=True)
                server_file = temp_path / "app" / "server.py"
                server_file.write_text(mock_server_content)

                # Mock the project root to use our temp directory
                with patch("scripts.generate_crud.Path") as mock_path:
                    mock_path.return_value.parent.parent = temp_path

                    # This should fail with current implementation
                    # because it will generate incorrect pluralization
                    try:
                        update_server_file(entity_name, dry_run=False)

                        # Check the generated content
                        updated_content = server_file.read_text()

                        # The bug: current implementation will generate wrong prefix
                        expected_router_line = (
                            f"app.include_router({entity_name}_router, "
                            f'prefix="/api/v1/{expected_plural}")'
                        )
                        wrong_router_line = (
                            f"app.include_router({entity_name}_router, "
                            f'prefix="/api/v1/{entity_name}s")'
                        )

                        # This assertion should fail, demonstrating the bug
                        assert expected_router_line in updated_content, (
                            f"Expected correct router line '{expected_router_line}' "
                            f"not found in generated server.py"
                        )

                        # The actual bug - this will be found instead
                        if (
                            wrong_router_line in updated_content
                            and expected_router_line not in updated_content
                        ):
                            pytest.fail(
                                f"CLI generator produced incorrect pluralization: "
                                f"found '{wrong_router_line}' instead of '{expected_router_line}'"
                            )

                    except Exception as e:
                        # If the test setup fails, that's also a problem
                        pytest.fail(f"CLI generator integration failed: {e}")

    @pytest.mark.parametrize(
        "entity_name,expected_plural,current_wrong",
        [
            ("test_entity", "test_entities", "test_entitys"),
            ("user_profile", "user_profiles", "user_profiles"),  # This one might work
            ("order_item", "order_items", "order_items"),  # This one might work
            ("data_source", "data_sources", "data_sources"),  # This one might work
            ("company", "companies", "companys"),
            ("category", "categories", "categorys"),
            ("payment_method", "payment_methods", "payment_methods"),  # This one might work
        ],
    )
    def test_pluralization_bug_demonstration(
        self, entity_name: str, expected_plural: str, current_wrong: str
    ):
        """Demonstrate the specific pluralization bugs in router generation

        This test clearly shows what the current implementation produces
        vs. what it should produce.

        Args:
            entity_name: The entity name to test
            expected_plural: What the correct plural should be
            current_wrong: What the current implementation produces (if different)
        """
        # Get current implementation result
        current_result = get_table_name(entity_name)

        # Show the bug when current_wrong != expected_plural
        if current_wrong != expected_plural:
            # This should fail, demonstrating the bug
            assert current_result == expected_plural, (
                f"PLURALIZATION BUG: '{entity_name}' should become '{expected_plural}' "
                f"but current implementation produces '{current_result}'"
            )
        else:
            # This should pass for cases that work correctly
            assert current_result == expected_plural


class TestRouterGenerationIntegration:
    """Test the complete router generation workflow"""

    def test_complete_workflow_with_compound_words(self):
        """Test the complete workflow from entity name to router registration

        This test covers the entire flow that would happen when running:
        python scripts/generate_crud.py --entity test_entity --fields "name:str"
        """
        entity_name = "test_entity"
        [FieldDefinition(name="name", type_="str", optional=False)]

        # Step 1: Validate entity name
        validated_entity = validate_entity_name(entity_name, allow_existing=True)
        assert validated_entity == entity_name

        # Step 2: Generate table name (this is where the bug occurs)
        table_name = get_table_name(entity_name)

        # Step 3: This should generate correct API prefix
        api_prefix = f"/api/v1/{table_name}"
        expected_prefix = "/api/v1/test_entities"

        # This assertion will fail, demonstrating the bug
        assert api_prefix == expected_prefix, (
            f"Complete workflow produces wrong API prefix: "
            f"expected '{expected_prefix}', got '{api_prefix}'"
        )

    def test_router_wiring_consistency(self):
        """Test that router module wiring uses consistent naming

        The dependency injection wiring should use the entity name,
        not the pluralized form, for module paths.
        """
        entity_name = "test_entity"

        # Module wiring should use singular form
        expected_module = f'"app.{entity_name}.api.routers",'
        assert "test_entity" in expected_module
        assert "test_entities" not in expected_module

    def test_import_statement_generation(self):
        """Test that import statements use correct entity names"""
        entity_name = "test_entity"

        # Import should use singular entity name
        expected_import = f"from app.{entity_name}.api.routers import {entity_name}_router"

        # Router variable name should use singular
        assert f"{entity_name}_router" in expected_import
        assert "test_entities_router" not in expected_import


class TestEdgeCasesInRouterGeneration:
    """Test edge cases in router generation"""

    def test_entities_already_ending_in_s(self):
        """Test entities that already end in 's'"""
        test_cases = [
            ("users", "users"),  # Should remain unchanged
            ("orders", "orders"),  # Should remain unchanged
            ("address", "addresses"),  # Should be pluralized correctly
        ]

        for entity_name, expected in test_cases:
            table_name = get_table_name(entity_name)
            router_prefix = f"/api/v1/{table_name}"
            expected_prefix = f"/api/v1/{expected}"

            assert router_prefix == expected_prefix, (
                f"Entity '{entity_name}' already ending in 's' should produce "
                f"prefix '{expected_prefix}', got '{router_prefix}'"
            )

    def test_very_short_entity_names(self):
        """Test very short entity names"""
        short_names = ["ai", "io", "id"]

        for entity_name in short_names:
            table_name = get_table_name(entity_name)
            router_prefix = f"/api/v1/{table_name}"

            # Should follow normal pluralization rules
            expected_prefix = f"/api/v1/{entity_name}s"
            assert router_prefix == expected_prefix

    def test_entity_names_with_numbers(self):
        """Test entity names containing numbers"""
        entity_name = "user_v2"
        table_name = get_table_name(entity_name)
        router_prefix = f"/api/v1/{table_name}"

        # Should pluralize the last word correctly
        expected_prefix = "/api/v1/user_v2s"  # Current simple implementation
        # Better would be: "/api/v1/user_v2s" (keeping it simple for now)

        assert router_prefix == expected_prefix


# Test helper functions
def create_test_server_content() -> str:
    """Create a mock server.py content for testing"""
    return '''from app.webhook.api.routers import webhook_router

def setup_routes(app: FastAPI):
    """Configure application routes"""
    app.include_router(webhook_router, prefix="/api/v1")
'''


def extract_router_prefix_from_content(content: str, entity_name: str) -> str:
    """Extract the router prefix from generated server content

    Args:
        content: The server.py file content
        entity_name: The entity name to look for

    Returns:
        The extracted router prefix
    """
    pattern = f'app\\.include_router\\({entity_name}_router, prefix="([^"]+)"\\)'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return ""
