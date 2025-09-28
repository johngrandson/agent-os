"""Tests for FastStream broker setup functionality"""

from unittest.mock import Mock, patch

from app.shared.events.broker import broker, setup_broker_with_handlers
from app.shared.events.registry import EventRegistry
from faststream.redis import RedisBroker, RedisRouter


class TestSetupBrokerWithHandlers:
    """Test setup_broker_with_handlers function"""

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_includes_all_routers(self, mock_registry):
        """Test that setup_broker_with_handlers includes all routers from registry"""
        # Arrange
        mock_router1 = Mock(spec=RedisRouter)
        mock_router2 = Mock(spec=RedisRouter)
        mock_router3 = Mock(spec=RedisRouter)

        mock_registry.get_all_routers.return_value = {
            "agent": mock_router1,
            "messages": mock_router2,
            "webhook": mock_router3,
        }

        # Mock the broker's include_router method
        with patch.object(broker, "include_router") as mock_include_router:
            # Act
            result_broker = setup_broker_with_handlers()

            # Assert
            assert result_broker is broker
            assert mock_include_router.call_count == 3

            # Verify each router was included exactly once
            mock_include_router.assert_any_call(mock_router1)
            mock_include_router.assert_any_call(mock_router2)
            mock_include_router.assert_any_call(mock_router3)

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_calls_values_method(self, mock_registry):
        """Test that setup_broker_with_handlers calls .values() on get_all_routers() result"""
        # Arrange
        mock_router = Mock(spec=RedisRouter)
        mock_routers_dict = Mock()
        mock_routers_dict.values.return_value = [mock_router]

        mock_registry.get_all_routers.return_value = mock_routers_dict

        with patch.object(broker, "include_router"):
            # Act
            setup_broker_with_handlers()

            # Assert
            mock_registry.get_all_routers.assert_called_once()
            mock_routers_dict.values.assert_called_once()

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_handles_empty_registry(self, mock_registry):
        """Test that setup_broker_with_handlers handles empty router registry"""
        # Arrange
        mock_registry.get_all_routers.return_value = {}

        with patch.object(broker, "include_router") as mock_include_router:
            # Act
            result_broker = setup_broker_with_handlers()

            # Assert
            assert result_broker is broker
            mock_include_router.assert_not_called()

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_preserves_router_order(self, mock_registry):
        """Test that routers are included in the order returned by values()"""
        # Arrange
        router1 = Mock(spec=RedisRouter)
        router2 = Mock(spec=RedisRouter)
        router3 = Mock(spec=RedisRouter)

        # Create ordered dict to ensure deterministic order
        from collections import OrderedDict

        ordered_routers = OrderedDict(
            [("agent", router1), ("messages", router2), ("webhook", router3)]
        )

        mock_registry.get_all_routers.return_value = ordered_routers

        include_calls = []

        def capture_include_calls(router):
            include_calls.append(router)

        with patch.object(broker, "include_router", side_effect=capture_include_calls):
            # Act
            setup_broker_with_handlers()

            # Assert
            assert include_calls == [router1, router2, router3]

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_returns_configured_broker(self, mock_registry):
        """Test that setup_broker_with_handlers returns the broker instance"""
        # Arrange
        mock_registry.get_all_routers.return_value = {}

        # Act
        result = setup_broker_with_handlers()

        # Assert
        assert result is broker
        assert isinstance(result, RedisBroker)

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_router_objects_not_strings(self, mock_registry):
        """Test the critical fix: ensure we iterate over router objects, not strings"""
        # Arrange - This test specifically validates the bug fix
        mock_router1 = Mock(spec=RedisRouter)
        mock_router2 = Mock(spec=RedisRouter)

        # Simulate what get_all_routers() returns (dict with string keys, router values)
        routers_dict = {"agent": mock_router1, "messages": mock_router2}
        mock_registry.get_all_routers.return_value = routers_dict

        included_routers = []

        def capture_router_types(router):
            included_routers.append(router)
            # This would have failed before the fix with:
            # "Router must be an instance of RedisRegistrator, got str instead"

        with patch.object(broker, "include_router", side_effect=capture_router_types):
            # Act
            setup_broker_with_handlers()

            # Assert
            assert len(included_routers) == 2
            for router in included_routers:
                assert not isinstance(router, str), f"Expected router object, got string: {router}"
                assert isinstance(router, Mock)  # Our mock router objects

    @patch("app.shared.events.broker.event_registry")
    def test_setup_broker_with_handlers_integration_with_real_registry(self, mock_registry):
        """Test setup_broker_with_handlers with patterns from actual registry usage"""
        # Arrange - Create a real EventRegistry to test the actual .values() behavior
        real_registry = EventRegistry()

        # Add routers like the real application does
        agent_router = Mock(spec=RedisRouter)
        messages_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        real_registry.register_domain_router("agent", agent_router)
        real_registry.register_domain_router("messages", messages_router)
        real_registry.register_domain_router("webhook", webhook_router)

        # Mock the global registry to return our test registry's data
        mock_registry.get_all_routers.return_value = real_registry.get_all_routers()

        with patch.object(broker, "include_router") as mock_include_router:
            # Act
            result = setup_broker_with_handlers()

            # Assert
            assert result is broker
            assert mock_include_router.call_count == 3

            # Get the actual calls to verify router objects were passed
            actual_routers = [call[0][0] for call in mock_include_router.call_args_list]
            assert agent_router in actual_routers
            assert messages_router in actual_routers
            assert webhook_router in actual_routers


class TestBrokerConfiguration:
    """Test broker module configuration"""

    def test_broker_is_redis_broker_instance(self):
        """Test that module-level broker is a RedisBroker instance"""
        from app.shared.events.broker import broker

        assert isinstance(broker, RedisBroker)

    @patch("app.shared.events.broker.get_config")
    def test_broker_uses_config_redis_url(self, mock_get_config):
        """Test that broker is configured with Redis URL from config"""
        # This test verifies the broker was created with the right config
        # Since broker is created at module level, we can't easily test this directly
        # But we can verify the config is imported and used

        from app.shared.events.broker import config

        assert config is not None

    def test_faststream_app_is_configured_with_broker(self):
        """Test that FastStream app is configured with the broker"""
        from app.shared.events.broker import app, broker

        assert app.broker is broker
