"""Unit tests for pluralization logic in CLI CRUD generator

These tests follow TDD principles and demonstrate the current pluralization bug
where compound words like 'test_entity' become 'test_entitys' instead of 'test_entities'.
"""

import pytest
from scripts.generate_crud import get_table_name


class TestPluralizationLogic:
    """Test suite for pluralization functionality"""

    @pytest.mark.parametrize(
        "input_word,expected",
        [
            # Simple cases that should work
            ("user", "users"),
            ("product", "products"),
            ("order", "orders"),
            ("item", "items"),
            # Current failure cases - compound words
            ("test_entity", "test_entities"),  # ❌ Currently fails: gets 'test_entitys'
            ("user_profile", "user_profiles"),  # ❌ Currently fails: gets 'user_profiles'
            ("order_item", "order_items"),  # ❌ Currently fails: gets 'order_items'
            ("data_source", "data_sources"),  # ❌ Currently fails: gets 'data_sources'
            # Special pluralization cases (English rules)
            ("company", "companies"),  # ❌ Currently fails: gets 'companys'
            ("category", "categories"),  # ❌ Currently fails: gets 'categorys'
            ("story", "stories"),  # ❌ Currently fails: gets 'storys'
            ("country", "countries"),  # ❌ Currently fails: gets 'countrys'
            # Words ending in 's' (should not be changed)
            ("status", "status"),  # Should work correctly
            ("series", "series"),  # Should work correctly
            ("news", "news"),  # Should work correctly
            # Complex compound words
            ("payment_method", "payment_methods"),  # ❌ Currently fails
            ("shipping_address", "shipping_addresses"),  # ❌ Currently fails
            ("user_activity", "user_activities"),  # ❌ Currently fails
        ],
    )
    def test_pluralization_logic(self, input_word: str, expected: str):
        """Test that pluralization handles various word types correctly

        This test demonstrates the current bug and will fail for compound words
        and special English pluralization rules.

        Args:
            input_word: The singular form to pluralize
            expected: The correct plural form
        """
        result = get_table_name(input_word)
        assert result == expected, (
            f"Pluralization failed for '{input_word}': expected '{expected}', got '{result}'"
        )

    def test_empty_string_handling(self):
        """Test edge case: empty string should be handled gracefully"""
        # Empty string should raise a ValueError (fail fast)
        with pytest.raises(ValueError, match="Cannot pluralize empty string"):
            get_table_name("")

    def test_single_character_handling(self):
        """Test edge case: single character handling"""
        result = get_table_name("a")
        assert result == "as"  # Simple case should work

    def test_underscores_only(self):
        """Test edge case: underscore-only string"""
        with pytest.raises((ValueError, IndexError)):
            # This should probably raise an error rather than create invalid output
            get_table_name("_")

    @pytest.mark.parametrize(
        "entity_ending_in_s",
        [
            "users",  # Already plural
            "orders",  # Already plural
            "categories",  # Already plural
            "companies",  # Already plural
            "test_entities",  # Already plural compound
        ],
    )
    def test_already_plural_words_unchanged(self, entity_ending_in_s: str):
        """Test that words already ending in 's' are not modified

        Args:
            entity_ending_in_s: Entity name already ending in 's'
        """
        result = get_table_name(entity_ending_in_s)
        assert result == entity_ending_in_s, (
            f"Already plural word '{entity_ending_in_s}' should remain unchanged, got '{result}'"
        )


class TestPluralizationIntegration:
    """Integration tests for pluralization in the context of CLI generation"""

    def test_compound_word_pluralization_for_api_routes(self):
        """Test that compound words are pluralized correctly for API routes

        This test demonstrates how the pluralization bug affects API route generation.
        """
        # Test the problematic case that started this issue
        test_cases = [
            ("test_entity", "test_entities"),
            ("user_profile", "user_profiles"),
            ("order_item", "order_items"),
            ("payment_method", "payment_methods"),
        ]

        for entity_name, expected_plural in test_cases:
            table_name = get_table_name(entity_name)

            # Simulate how this would be used in router prefix generation
            router_prefix = f"/api/v1/{table_name}"
            expected_prefix = f"/api/v1/{expected_plural}"

            assert router_prefix == expected_prefix, (
                f"Router prefix generation failed for '{entity_name}': "
                f"expected '{expected_prefix}', got '{router_prefix}'"
            )

    def test_table_name_consistency_with_model_generation(self):
        """Test that table names are consistently pluralized across all uses"""
        entity_name = "test_entity"

        # The same pluralization logic should be used everywhere
        table_name_1 = get_table_name(entity_name)
        table_name_2 = get_table_name(entity_name)

        assert table_name_1 == table_name_2, "Pluralization should be deterministic"

        # Should be 'test_entities', not 'test_entitys'
        expected = "test_entities"
        assert table_name_1 == expected, (
            f"Table name for '{entity_name}' should be '{expected}', got '{table_name_1}'"
        )


@pytest.fixture
def sample_entity_names():
    """Fixture providing common entity names for testing"""
    return [
        "user",
        "product",
        "order",
        "category",
        "company",
        "test_entity",
        "user_profile",
        "order_item",
        "data_source",
        "payment_method",
        "shipping_address",
        "user_activity",
    ]


class TestPluralizationRegressionPrevention:
    """Tests to prevent regression after fixing the pluralization issue"""

    def test_simple_nouns_still_work_after_fix(self, sample_entity_names):
        """Ensure simple noun pluralization continues to work after compound word fix"""
        simple_nouns = ["user", "product", "order", "item"]

        for noun in simple_nouns:
            if noun in sample_entity_names:
                result = get_table_name(noun)
                expected = f"{noun}s"
                assert result == expected, f"Simple noun '{noun}' should become '{expected}'"

    def test_no_double_pluralization(self):
        """Test that applying pluralization twice doesn't break things"""
        entity_name = "user"
        first_pluralization = get_table_name(entity_name)  # Should be "users"
        second_pluralization = get_table_name(first_pluralization)  # Should remain "users"

        assert first_pluralization == "users"
        assert second_pluralization == "users", "Double pluralization should not change result"
