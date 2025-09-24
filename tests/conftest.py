"""Pytest configuration and fixtures for pluralization TDD tests

This file contains shared test fixtures and configuration for the
test-driven development of the pluralization fix.
"""

import sys
from pathlib import Path

import pytest


# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root_path():
    """Provide the project root path for tests"""
    return project_root


@pytest.fixture
def sample_entity_names():
    """Provide common entity names for testing pluralization"""
    return [
        # Simple nouns (should work with current implementation)
        "user",
        "product",
        "order",
        "item",
        # Compound words (currently broken)
        "test_entity",
        "user_profile",
        "order_item",
        "data_source",
        "payment_method",
        "shipping_address",
        # Special English pluralization (currently broken)
        "company",
        "category",
        "story",
        "country",
        # Words ending in 's' (should work with current implementation)
        "status",
        "series",
        "news",
        "address",
    ]


@pytest.fixture
def expected_pluralizations():
    """Provide correct pluralization mappings"""
    return {
        # Simple nouns
        "user": "users",
        "product": "products",
        "order": "orders",
        "item": "items",
        # Compound words
        "test_entity": "test_entities",
        "user_profile": "user_profiles",
        "order_item": "order_items",
        "data_source": "data_sources",
        "payment_method": "payment_methods",
        "shipping_address": "shipping_addresses",
        "user_activity": "user_activities",
        # Special English pluralization
        "company": "companies",
        "category": "categories",
        "story": "stories",
        "country": "countries",
        # Words ending in 's' (no change)
        "status": "status",
        "series": "series",
        "news": "news",
        "address": "address",
    }


@pytest.fixture
def current_wrong_pluralizations():
    """Provide what the current implementation incorrectly produces"""
    return {
        # These work correctly with current implementation
        "user": "users",
        "product": "products",
        "order": "orders",
        "item": "items",
        "status": "status",
        "series": "series",
        "news": "news",
        # These are wrong with current implementation
        "test_entity": "test_entitys",  # Should be "test_entities"
        "user_profile": "user_profiles",  # Actually works correctly
        "order_item": "order_items",  # Actually works correctly
        "data_source": "data_sources",  # Actually works correctly
        "payment_method": "payment_methods",  # Actually works correctly
        "shipping_address": "shipping_addresses",  # Actually works correctly
        "user_activity": "user_activitys",  # Should be "user_activities"
        "company": "companys",  # Should be "companies"
        "category": "categorys",  # Should be "categories"
        "story": "storys",  # Should be "stories"
        "country": "countrys",  # Should be "countries"
    }


# Test markers for different categories of tests
pytest_plugins: list[str] = []


# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests for individual functions")
    config.addinivalue_line("markers", "integration: Integration tests for CLI generator")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "pluralization: Tests related to pluralization logic")
    config.addinivalue_line("markers", "failing: Tests that demonstrate current bugs (should fail)")
    config.addinivalue_line("markers", "compound_words: Tests for compound word pluralization")
    config.addinivalue_line(
        "markers", "english_rules: Tests for special English pluralization rules"
    )


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names and locations"""
    for item in items:
        # Add markers based on test location
        if "unit" in item.fspath.basename:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        elif "api" in item.fspath.basename:
            item.add_marker(pytest.mark.api)

        # Add markers based on test names
        if "pluralization" in item.name.lower():
            item.add_marker(pytest.mark.pluralization)
        if "compound" in item.name.lower():
            item.add_marker(pytest.mark.compound_words)
        if "english" in item.name.lower() or "special" in item.name.lower():
            item.add_marker(pytest.mark.english_rules)
