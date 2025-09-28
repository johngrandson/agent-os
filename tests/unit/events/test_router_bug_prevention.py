"""Tests specifically for preventing the router string vs object bug"""

from unittest.mock import Mock, patch

import pytest
from app.shared.events.broker import setup_broker_with_handlers
from app.shared.events.registry import EventRegistry
from faststream.exceptions import SetupError
from faststream.redis import RedisRouter


class TestRouterBugPrevention:
    """Tests specifically designed to prevent the router string bug from recurring"""

    def test_get_all_routers_values_returns_router_objects_not_strings(self):
        """Critical test: ensure get_all_routers().values() returns router objects, not strings"""
        # Arrange
        registry = EventRegistry()
        mock_router1 = Mock(spec=RedisRouter)
        mock_router2 = Mock(spec=RedisRouter)
        mock_router3 = Mock(spec=RedisRouter)

        # Register routers like the actual application
        registry.register_domain_router("agent", mock_router1)
        registry.register_domain_router("messages", mock_router2)
        registry.register_domain_router("webhook", mock_router3)

        # Act - Get router values (this is what the fixed code does)
        router_values = list(registry.get_all_routers().values())

        # Assert - Verify we get objects, not strings
        assert len(router_values) == 3
        for router in router_values:
            assert not isinstance(router, str), f"Expected router object, got string: {router}"
            assert hasattr(router, "include_router") or router in [
                mock_router1,
                mock_router2,
                mock_router3,
            ]

    def test_get_all_routers_keys_vs_values_bug_demonstration(self):
        """Demonstrate the difference between keys() (bad) and values() (good)"""
        # Arrange
        registry = EventRegistry()
        mock_router = Mock(spec=RedisRouter)

        registry.register_domain_router("test_domain", mock_router)

        # Act
        all_routers = registry.get_all_routers()
        router_keys = list(all_routers.keys())  # This was the bug - iterating over keys
        router_values = list(all_routers.values())  # This is the fix - iterating over values

        # Assert
        assert len(router_keys) == 1
        assert len(router_values) == 1

        # Keys are strings (domain names) - THIS IS WHAT CAUSED THE BUG
        assert isinstance(router_keys[0], str)
        assert router_keys[0] == "test_domain"

        # Values are router objects - THIS IS THE FIX
        assert not isinstance(router_values[0], str)
        assert router_values[0] is mock_router

    def test_broker_include_router_rejects_string_arguments(self):
        """Test that broker.include_router() would reject string arguments"""
        # This test simulates what would happen if we passed strings to include_router
        # (This was the original error that led us to discover the bug)

        from app.shared.events.broker import broker

        # Act & Assert - Passing a string should cause an error
        with pytest.raises((TypeError, SetupError, AttributeError)):
            # This would fail with something like:
            # "Router must be an instance of RedisRegistrator, got str instead"
            broker.include_router("this_is_a_string_not_a_router")

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_fixed_iteration_pattern(self, mock_registry):
        """Test that setup_broker_with_handlers uses the fixed iteration pattern"""
        # Arrange - Create registry data that would expose the bug
        mock_router1 = Mock(spec=RedisRouter)
        mock_router2 = Mock(spec=RedisRouter)

        # This simulates the actual return value from get_all_routers()
        routers_dict = {
            "agent": mock_router1,  # Key is string (would cause bug if used)
            "messages": mock_router2,  # Value is router object (correct)
        }

        mock_registry.get_all_routers.return_value = routers_dict

        # Create a strict mock that fails if passed strings
        def strict_include_router(router):
            if isinstance(router, str):
                msg = f"Router must be an instance of RedisRouter, got str instead: {router}"
                raise SetupError(msg)

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock(side_effect=strict_include_router)

            # Act - This should work because we use .values(), not direct iteration
            try:
                setup_broker_with_handlers()

                # Assert - If we get here, the fix is working
                assert mock_broker.include_router.call_count == 2

                # Verify we passed router objects, not strings
                calls = [call[0][0] for call in mock_broker.include_router.call_args_list]
                assert mock_router1 in calls
                assert mock_router2 in calls

                # Verify no strings were passed
                for router in calls:
                    assert not isinstance(router, str)

            except SetupError as e:
                if "got str instead" in str(e):
                    pytest.fail(
                        "BUG STILL EXISTS: setup_broker_with_handlers is passing strings "
                        "instead of router objects. The fix is not working."
                    )
                else:
                    raise

    def test_reproduce_original_bug_scenario(self):
        """Reproduce the exact scenario that caused the original bug"""
        # This test demonstrates what happened before the fix

        # Arrange - Create the same registry setup as in the real app
        registry = EventRegistry()

        # Add the same routers that exist in the real app
        agent_router = Mock(spec=RedisRouter)
        messages_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        registry.register_domain_router("agent", agent_router)
        registry.register_domain_router("messages", messages_router)
        registry.register_domain_router("webhook", webhook_router)

        # Act - Get all routers (this is what setup_broker_with_handlers calls)
        all_routers = registry.get_all_routers()

        # Demonstrate the OLD way (that caused the bug)
        old_way_iteration = list(all_routers)  # Iterating directly over dict gives keys

        # Demonstrate the NEW way (the fix)
        new_way_iteration = list(all_routers.values())  # Using .values() gives router objects

        # Assert
        # Old way gives strings (domain names) - THIS CAUSED THE BUG
        for item in old_way_iteration:
            assert isinstance(item, str)
            assert item in ["agent", "messages", "webhook"]

        # New way gives router objects - THIS IS THE FIX
        for router in new_way_iteration:
            assert not isinstance(router, str)
            assert router in [agent_router, messages_router, webhook_router]

    def test_all_domain_routers_are_objects_not_strings(self):
        """Test that all domain routers in the system are objects, not strings"""
        # This test verifies the fix works with all known domain routers

        registry = EventRegistry()

        # Create mock routers for all known domains
        domains_and_routers = {
            "agent": Mock(spec=RedisRouter),
            "messages": Mock(spec=RedisRouter),
            "webhook": Mock(spec=RedisRouter),
        }

        # Register all domains
        for domain, router in domains_and_routers.items():
            registry.register_domain_router(domain, router)

        # Act - Use the same pattern as the fixed code
        router_values = list(registry.get_all_routers().values())

        # Assert
        assert len(router_values) == len(domains_and_routers)

        for router in router_values:
            # Each should be a router object, not a string
            assert not isinstance(router, str)
            # Each should be one of our mock routers
            assert router in domains_and_routers.values()

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_prevents_string_router_error(self, mock_registry):
        """Final integration test: ensure setup_broker_with_handlers prevents the original error"""
        # Arrange - Set up the exact scenario that caused the original failure
        mock_agent_router = Mock(spec=RedisRouter)
        mock_messages_router = Mock(spec=RedisRouter)
        mock_webhook_router = Mock(spec=RedisRouter)

        mock_registry.get_all_routers.return_value = {
            "agent": mock_agent_router,
            "messages": mock_messages_router,
            "webhook": mock_webhook_router,
        }

        # Create a mock broker that simulates the original FastStream error
        with patch("app.shared.events.broker.broker") as mock_broker:

            def simulate_faststream_error(router):
                if isinstance(router, str):
                    msg = "Router must be an instance of RedisRegistrator, got str instead"
                    raise SetupError(msg)
                # If we get a proper router object, just record the call
                return

            mock_broker.include_router = Mock(side_effect=simulate_faststream_error)

            # Act - This should NOT raise SetupError because we're using the fix
            try:
                result = setup_broker_with_handlers()

                # Assert - Success means the fix is working
                assert result is mock_broker
                assert mock_broker.include_router.call_count == 3

                # Verify all calls were with router objects
                for call_args in mock_broker.include_router.call_args_list:
                    router_arg = call_args[0][0]
                    assert router_arg in [
                        mock_agent_router,
                        mock_messages_router,
                        mock_webhook_router,
                    ]

            except SetupError as e:
                if "got str instead" in str(e):
                    pytest.fail(
                        f"REGRESSION: The original bug has returned! Error: {e}\n"
                        "setup_broker_with_handlers is passing router domain names (strings) "
                        "instead of router objects to broker.include_router()"
                    )
                else:
                    # Re-raise if it's a different SetupError
                    raise
