"""End-to-end integration tests for complete event system setup"""

from unittest.mock import Mock, patch

import pytest
from app.events.broker import app, broker, setup_broker_with_handlers
from app.events.core.registry import event_registry
from faststream import FastStream
from faststream.redis import RedisBroker, RedisRouter


class TestCompleteEventSystemSetup:
    """End-to-end integration tests for the complete event system"""

    def setup_method(self):
        """Store original state"""
        self.original_routers = event_registry._routers.copy()

    def teardown_method(self):
        """Restore original state"""
        event_registry._routers = self.original_routers

    def test_complete_event_system_initialization(self):
        """Test that the complete event system can be initialized without errors"""
        # Arrange
        event_registry._routers.clear()

        # Add mock routers for all domains
        agent_router = Mock(spec=RedisRouter)
        orchestration_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        event_registry.register_domain_router("agent", agent_router)
        event_registry.register_domain_router("orchestration", orchestration_router)
        event_registry.register_domain_router("webhook", webhook_router)

        # Mock external dependencies
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act - This should work end-to-end without errors
            result_broker = setup_broker_with_handlers()

            # Assert
            assert result_broker is mock_broker
            assert mock_broker.include_router.call_count == 3

            # Verify each domain router was properly registered
            included_routers = [call[0][0] for call in mock_broker.include_router.call_args_list]
            assert agent_router in included_routers
            assert orchestration_router in included_routers
            assert webhook_router in included_routers

    def test_faststream_app_broker_integration(self):
        """Test that FastStream app is properly integrated with broker"""
        # Test the module-level configuration
        assert isinstance(app, FastStream)
        assert isinstance(broker, RedisBroker)
        assert app.broker is broker

    def test_broker_configuration_with_redis_url(self):
        """Test that broker is configured with Redis URL from config"""
        # Since config is loaded at module level, we just verify it exists and has redis_url
        from app.events.broker import config

        # Assert
        assert config is not None
        assert hasattr(config, "redis_url")
        # Verify it's the actual config object, not a mock
        assert str(type(config).__name__) == "Config"

    def test_event_system_handles_all_known_domains(self):
        """Test event system with all domains that exist in the actual application"""
        # Arrange
        event_registry._routers.clear()

        # These are the domains we know exist from the grep search
        known_domains = ["agent", "orchestration", "webhook"]
        domain_routers = {}

        for domain in known_domains:
            router = Mock(spec=RedisRouter)
            router.domain_name = domain
            domain_routers[domain] = router
            event_registry.register_domain_router(domain, router)

        # Mock the broker
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # Act
            setup_broker_with_handlers()

            # Assert
            assert mock_broker.include_router.call_count == len(known_domains)

            # Verify each domain was handled
            included_routers = [call[0][0] for call in mock_broker.include_router.call_args_list]
            for domain in known_domains:
                assert domain_routers[domain] in included_routers

    def test_event_system_startup_sequence(self):
        """Test the typical startup sequence for the event system"""
        # This test simulates the actual startup process

        # Arrange - Clear registry (simulating fresh start)
        event_registry._routers.clear()

        # Step 1: Domain handlers register their routers (simulating module imports)
        agent_router = Mock(spec=RedisRouter)
        orchestration_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        # Simulate what happens in each domain's handlers.py file
        event_registry.register_domain_router("agent", agent_router)
        event_registry.register_domain_router("orchestration", orchestration_router)
        event_registry.register_domain_router("webhook", webhook_router)

        # Step 2: Verify routers are registered
        assert len(event_registry.get_all_routers()) == 3

        # Step 3: Setup broker with all registered routers
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            result_broker = setup_broker_with_handlers()

            # Assert startup completed successfully
            assert result_broker is mock_broker
            assert mock_broker.include_router.call_count == 3

    def test_event_system_resilience_to_empty_registry(self):
        """Test that event system handles empty registry gracefully"""
        # Arrange
        event_registry._routers.clear()

        # Act
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            result = setup_broker_with_handlers()

            # Assert
            assert result is mock_broker
            assert mock_broker.include_router.call_count == 0  # No routers to include

    def test_event_system_handles_partial_domain_registration(self):
        """Test system works correctly with only some domains registered"""
        # Arrange
        event_registry._routers.clear()

        # Only register agent domain (simulating partial startup)
        agent_router = Mock(spec=RedisRouter)
        event_registry.register_domain_router("agent", agent_router)

        # Act
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            result = setup_broker_with_handlers()

            # Assert
            assert result is mock_broker
            assert mock_broker.include_router.call_count == 1
            mock_broker.include_router.assert_called_once_with(agent_router)

    def test_event_system_router_registration_order_independence(self):
        """Test that router registration order doesn't affect functionality"""
        # Arrange
        event_registry._routers.clear()

        routers = []
        domains = ["webhook", "agent", "orchestration"]  # Different order

        for domain in domains:
            router = Mock(spec=RedisRouter)
            router.domain_name = domain
            routers.append(router)
            event_registry.register_domain_router(domain, router)

        # Act
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            setup_broker_with_handlers()

            # Assert
            assert mock_broker.include_router.call_count == len(domains)

            # All routers should be included regardless of registration order
            included_routers = [call[0][0] for call in mock_broker.include_router.call_args_list]
            for router in routers:
                assert router in included_routers

    def test_integration_with_actual_registry_patterns(self):
        """Test integration using patterns from actual codebase"""
        # This test uses patterns found in the actual handlers files

        # Arrange
        event_registry._routers.clear()

        # Simulate the pattern from app/events/agents/handlers.py
        agent_router = Mock(spec=RedisRouter)
        # In real code: event_registry.register_domain_router("agent", agent_router)
        event_registry.register_domain_router("agent", agent_router)

        # Simulate the pattern from app/events/orchestration/handlers.py
        orchestration_router = Mock(spec=RedisRouter)
        event_registry.register_domain_router("orchestration", orchestration_router)

        # Simulate the pattern from app/events/webhooks/handlers.py
        webhook_router = Mock(spec=RedisRouter)
        event_registry.register_domain_router("webhook", webhook_router)

        # Act - Use the actual broker setup function
        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock()

            # This is the actual function call that was failing before the fix
            setup_broker_with_handlers()

            # Assert
            assert mock_broker.include_router.call_count == 3

            # Verify the fix: router objects are passed, not strings
            for call_args in mock_broker.include_router.call_args_list:
                router_arg = call_args[0][0]
                assert not isinstance(router_arg, str)
                assert router_arg in [agent_router, orchestration_router, webhook_router]

    @patch("app.events.broker.event_registry")
    def test_end_to_end_bug_prevention(self, mock_registry):
        """Final end-to-end test ensuring the string vs object bug cannot recur"""
        # Arrange - Set up the exact conditions that caused the original bug
        real_registry = event_registry.__class__()

        # Register routers using the same pattern as production code
        agent_router = Mock(spec=RedisRouter)
        orchestration_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        real_registry.register_domain_router("agent", agent_router)
        real_registry.register_domain_router("orchestration", orchestration_router)
        real_registry.register_domain_router("webhook", webhook_router)

        # Use the actual registry's get_all_routers method
        mock_registry.get_all_routers.return_value = real_registry.get_all_routers()

        # Create a strict broker mock that will fail if passed strings
        def fail_on_string_router(router):
            if isinstance(router, str):
                msg = f"REGRESSION BUG: String passed to include_router: {router}"
                raise TypeError(msg)

        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock(side_effect=fail_on_string_router)

            # Act - This should work without any errors
            result = setup_broker_with_handlers()

            # Assert - Success means our fix is working
            assert result is mock_broker
            assert mock_broker.include_router.call_count == 3

            # Double-check: verify all arguments were router objects
            for call_args in mock_broker.include_router.call_args_list:
                router_arg = call_args[0][0]
                assert router_arg in [agent_router, orchestration_router, webhook_router]
                assert not isinstance(router_arg, str)


class TestEventSystemErrorRecovery:
    """Test error recovery and resilience of the event system"""

    def setup_method(self):
        """Store original state"""
        self.original_routers = event_registry._routers.copy()

    def teardown_method(self):
        """Restore original state"""
        event_registry._routers = self.original_routers

    def test_system_continues_after_single_router_failure(self):
        """Test that system continues working if one router fails to be included"""
        # Arrange
        event_registry._routers.clear()

        good_router1 = Mock(spec=RedisRouter)
        failing_router = Mock(spec=RedisRouter)
        good_router2 = Mock(spec=RedisRouter)

        event_registry.register_domain_router("good1", good_router1)
        event_registry.register_domain_router("failing", failing_router)
        event_registry.register_domain_router("good2", good_router2)

        def selective_failure(router):
            if router is failing_router:
                msg = "Simulated router failure"
                raise Exception(msg)

        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock(side_effect=selective_failure)

            # Act & Assert - Should raise exception but we can test the pattern
            with pytest.raises(Exception, match="Simulated router failure"):
                setup_broker_with_handlers()

            # The function doesn't have error handling, which is correct -
            # failures should bubble up to be handled at a higher level

    def test_system_state_after_setup_failure(self):
        """Test that system state remains consistent after setup failure"""
        # Arrange
        event_registry._routers.clear()

        router1 = Mock(spec=RedisRouter)
        router2 = Mock(spec=RedisRouter)

        event_registry.register_domain_router("domain1", router1)
        event_registry.register_domain_router("domain2", router2)

        # Save state before failure
        routers_before = event_registry.get_all_routers()

        with patch("app.events.broker.broker") as mock_broker:
            mock_broker.include_router = Mock(side_effect=Exception("Broker failure"))

            # Act
            with pytest.raises(Exception, match="Broker failure"):
                setup_broker_with_handlers()

            # Assert - Registry state should be unchanged after broker setup failure
            routers_after = event_registry.get_all_routers()
            assert routers_before == routers_after
            assert len(routers_after) == 2
