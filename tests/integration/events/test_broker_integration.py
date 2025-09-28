"""Integration tests for FastStream broker router registration"""

from unittest.mock import Mock, patch

import pytest
from app.shared.events.broker import setup_broker_with_handlers
from app.shared.events.registry import event_registry
from faststream.redis import RedisRouter


class TestBrokerRouterIntegration:
    """Integration tests for broker router registration with all domains"""

    def setup_method(self):
        """Clean up registry state before each test"""
        # Store original routers to restore after test
        self.original_routers = event_registry._routers.copy()

    def teardown_method(self):
        """Restore original registry state after each test"""
        event_registry._routers = self.original_routers

    def test_setup_broker_with_all_registered_domains(self):
        """Test that broker setup works with all actual domain routers"""
        # Arrange - Clear registry and add mock routers for all known domains
        event_registry._routers.clear()

        agent_router = Mock(spec=RedisRouter)
        messages_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        event_registry.register_domain_router("agent", agent_router)
        event_registry.register_domain_router("messages", messages_router)
        event_registry.register_domain_router("webhook", webhook_router)

        # Mock the broker's include_router to track calls
        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act
            result = setup_broker_with_handlers()

            # Assert
            assert result is mock_broker
            assert mock_broker.include_router.call_count == 3

            # Verify all domain routers were included
            actual_calls = [call[0][0] for call in mock_broker.include_router.call_args_list]
            assert agent_router in actual_calls
            assert messages_router in actual_calls
            assert webhook_router in actual_calls

    def test_broker_setup_with_dynamic_router_registration(self):
        """Test broker setup adapts to routers registered at runtime"""
        # Arrange - Start with empty registry
        event_registry._routers.clear()

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act 1 - Setup with no routers
            setup_broker_with_handlers()

            # Assert 1 - No routers included
            assert mock_broker.include_router.call_count == 0

            # Arrange 2 - Add a router
            new_router = Mock(spec=RedisRouter)
            event_registry.register_domain_router("dynamic", new_router)

            # Act 2 - Setup again
            mock_broker.include_router.reset_mock()
            setup_broker_with_handlers()

            # Assert 2 - New router is included
            assert mock_broker.include_router.call_count == 1
            mock_broker.include_router.assert_called_once_with(new_router)

    def test_broker_setup_handles_router_replacement(self):
        """Test broker setup handles when domain routers are replaced"""
        # Arrange
        event_registry._routers.clear()

        old_router = Mock(spec=RedisRouter)
        new_router = Mock(spec=RedisRouter)

        event_registry.register_domain_router("test_domain", old_router)

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act 1 - Setup with old router
            setup_broker_with_handlers()

            # Assert 1
            mock_broker.include_router.assert_called_once_with(old_router)

            # Arrange 2 - Replace router
            event_registry.register_domain_router("test_domain", new_router)
            mock_broker.include_router.reset_mock()

            # Act 2 - Setup with new router
            setup_broker_with_handlers()

            # Assert 2 - New router is used, not old one
            mock_broker.include_router.assert_called_once_with(new_router)

            # Verify old router was not called again
            calls = [call[0][0] for call in mock_broker.include_router.call_args_list]
            assert new_router in calls
            assert old_router not in calls

    def test_router_registration_maintains_domain_isolation(self):
        """Test that different domains maintain separate routers"""
        # Arrange
        event_registry._routers.clear()

        agent_router = Mock(spec=RedisRouter)
        messages_router = Mock(spec=RedisRouter)

        # Act
        event_registry.register_domain_router("agent", agent_router)
        event_registry.register_domain_router("messages", messages_router)

        # Assert
        assert event_registry.get_router("agent") is agent_router
        assert event_registry.get_router("messages") is messages_router
        assert event_registry.get_router("agent") is not messages_router

    def test_multiple_broker_setups_are_idempotent(self):
        """Test that multiple calls to setup_broker_with_handlers work correctly"""
        # Arrange
        event_registry._routers.clear()

        router1 = Mock(spec=RedisRouter)
        router2 = Mock(spec=RedisRouter)
        event_registry.register_domain_router("domain1", router1)
        event_registry.register_domain_router("domain2", router2)

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act - Call setup multiple times
            setup_broker_with_handlers()
            setup_broker_with_handlers()
            setup_broker_with_handlers()

            # Assert - Each call should include all routers
            assert mock_broker.include_router.call_count == 6  # 3 calls * 2 routers

            # Verify each router was included in each call
            all_calls = [call[0][0] for call in mock_broker.include_router.call_args_list]
            assert all_calls.count(router1) == 3
            assert all_calls.count(router2) == 3


class TestBrokerRegistryIntegration:
    """Test integration between broker and actual event registry"""

    def setup_method(self):
        """Store original registry state"""
        self.original_routers = event_registry._routers.copy()

    def teardown_method(self):
        """Restore original registry state"""
        event_registry._routers = self.original_routers

    def test_broker_uses_global_event_registry(self):
        """Test that broker setup uses the global event registry instance"""
        # Arrange
        event_registry._routers.clear()
        test_router = Mock(spec=RedisRouter)
        event_registry.register_domain_router("test", test_router)

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act
            setup_broker_with_handlers()

            # Assert
            mock_broker.include_router.assert_called_once_with(test_router)

    def test_broker_setup_reflects_current_registry_state(self):
        """Test that broker setup always reflects the current state of registry"""
        # Arrange
        event_registry._routers.clear()

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act 1 - Setup with empty registry
            setup_broker_with_handlers()
            first_call_count = mock_broker.include_router.call_count

            # Act 2 - Add router and setup again
            router = Mock(spec=RedisRouter)
            event_registry.register_domain_router("new_domain", router)

            mock_broker.include_router.reset_mock()
            setup_broker_with_handlers()

            # Assert
            assert first_call_count == 0
            assert mock_broker.include_router.call_count == 1
            mock_broker.include_router.assert_called_once_with(router)

    def test_registry_router_isolation_in_broker_setup(self):
        """Test that each domain's router is independently managed in broker setup"""
        # Arrange
        event_registry._routers.clear()

        # Register multiple routers
        routers = {}
        domains = ["agent", "messages", "webhook", "custom"]

        for domain in domains:
            router = Mock(spec=RedisRouter)
            router.domain_name = domain  # Add identifier for testing
            routers[domain] = router
            event_registry.register_domain_router(domain, router)

        with patch("app.shared.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act
            setup_broker_with_handlers()

            # Assert
            assert mock_broker.include_router.call_count == len(domains)

            included_routers = [call[0][0] for call in mock_broker.include_router.call_args_list]

            # Verify each router was included exactly once
            for domain in domains:
                assert routers[domain] in included_routers

            # Verify no duplicates
            assert len(included_routers) == len(set(included_routers))


class TestBrokerSetupErrorHandling:
    """Test error handling in broker setup"""

    def setup_method(self):
        """Store original registry state"""
        self.original_routers = event_registry._routers.copy()

    def teardown_method(self):
        """Restore original registry state"""
        event_registry._routers = self.original_routers

    def test_broker_setup_handles_corrupted_registry_gracefully(self):
        """Test that broker setup works correctly even if registry has invalid entries"""
        # Note: This test demonstrates that our fix (.values()) prevents issues
        # even if the registry somehow gets corrupted with invalid data

        # Arrange
        event_registry._routers.clear()

        # Add valid routers first
        valid_router1 = Mock(spec=RedisRouter)
        valid_router2 = Mock(spec=RedisRouter)
        event_registry.register_domain_router("valid1", valid_router1)
        event_registry.register_domain_router("valid2", valid_router2)

        # Manually add an invalid entry (this simulates corruption)
        # This should NEVER happen in normal operation, but tests robustness
        event_registry._routers["corrupted"] = "this_is_a_string_not_a_router"

        with patch("app.shared.events.broker.broker") as mock_broker:

            def strict_include_router(router):
                if isinstance(router, str):
                    msg = f"Router must be an instance of RedisRouter, got str instead: {router}"
                    raise TypeError(msg)
                return

            mock_broker.include_router = Mock(side_effect=strict_include_router)

            # Act - This should work because .values() only gets valid router objects
            # The corrupted string value will be included in .values() but should be caught
            with pytest.raises(TypeError, match="Router must be an instance of RedisRouter"):
                setup_broker_with_handlers()

            # This test shows that corrupted data would be caught, which is the expected behavior
            # The important thing is that our fix doesn't accidentally pass strings from keys
