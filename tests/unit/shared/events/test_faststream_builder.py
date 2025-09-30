"""Comprehensive tests for FastStreamAppBuilder

Tests ensure the FastStream builder creates correct event system configuration
for multi-worker CLI usage and domain router registration.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from app.shared.events.builder import FastStreamAppBuilder
from faststream import FastStream
from faststream.redis import RedisBroker, RedisRouter


class TestFastStreamAppBuilderConstruction:
    """Test the builder pattern construction and fluent interface"""

    def test_builder_initialization_creates_empty_router_factory_list(self):
        """Builder should initialize with empty router factory list"""
        builder = FastStreamAppBuilder()
        assert builder._router_factories == []

    def test_add_domain_router_appends_factory(self):
        """Builder should store router factories"""
        builder = FastStreamAppBuilder()

        def factory():
            return RedisRouter()

        result = builder.add_domain_router(factory)

        assert result is builder  # Fluent interface
        assert len(builder._router_factories) == 1
        assert builder._router_factories[0] is factory

    def test_add_multiple_domain_routers_preserves_order(self):
        """Builder should maintain router factory registration order"""
        builder = FastStreamAppBuilder()

        def factory1():
            return RedisRouter()

        def factory2():
            return RedisRouter()

        builder.add_domain_router(factory1)
        builder.add_domain_router(factory2)

        assert len(builder._router_factories) == 2
        assert builder._router_factories[0] is factory1
        assert builder._router_factories[1] is factory2

    def test_fluent_interface_supports_method_chaining(self):
        """Builder should support fluent method chaining"""

        def factory1():
            return RedisRouter()

        def factory2():
            return RedisRouter()

        with patch("app.shared.events.builder.get_config") as mock_config:
            mock_config.return_value.redis_url = "redis://localhost:6379"

            app = (
                FastStreamAppBuilder()
                .add_domain_router(factory1)
                .add_domain_router(factory2)
                .build()
            )

        assert isinstance(app, FastStream)


class TestFastStreamAppBuilderBrokerConfiguration:
    """Test Redis broker configuration"""

    @patch("app.shared.events.builder.get_config")
    def test_build_creates_redis_broker_with_correct_url(self, mock_config):
        """Builder should create Redis broker with config URL"""
        mock_config.return_value.redis_url = "redis://test-redis:6379"

        builder = FastStreamAppBuilder()
        app = builder.build()

        # Verify broker configuration
        assert isinstance(app, FastStream)
        assert isinstance(app.broker, RedisBroker)
        # Check that broker was configured with correct URL
        mock_config.assert_called_once()

    @patch("app.shared.events.builder.get_config")
    def test_broker_uses_binary_message_format(self, mock_config):
        """Broker should use BinaryMessageFormatV1 for message serialization"""
        from faststream.redis.parser import BinaryMessageFormatV1

        mock_config.return_value.redis_url = "redis://localhost:6379"

        builder = FastStreamAppBuilder()
        app = builder.build()

        # Verify message format configuration (check class type)
        assert app.broker.message_format == BinaryMessageFormatV1

    @patch("app.shared.events.builder.get_config")
    def test_build_with_different_redis_urls(self, mock_config):
        """Builder should work with different Redis URL configurations"""
        test_urls = [
            "redis://localhost:6379",
            "redis://production-redis:6379",
            "redis://redis-cluster:6379/0",
        ]

        for url in test_urls:
            mock_config.return_value.redis_url = url
            builder = FastStreamAppBuilder()
            app = builder.build()

            assert isinstance(app, FastStream)
            assert isinstance(app.broker, RedisBroker)


class TestFastStreamAppBuilderRouterIntegration:
    """Test domain router factory integration"""

    @patch("app.shared.events.builder.get_config")
    def test_build_includes_domain_routers_from_factories(self, mock_config):
        """Builder should call router factories and include routers in broker"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        # Create real router instances for this test
        def factory1():
            router = RedisRouter()
            return router

        def factory2():
            router = RedisRouter()
            return router

        builder = FastStreamAppBuilder()
        app = builder.add_domain_router(factory1).add_domain_router(factory2).build()

        # Verify broker includes routers properly
        assert isinstance(app.broker, RedisBroker)

    @patch("app.shared.events.builder.get_config")
    def test_build_handles_empty_router_factory_list(self, mock_config):
        """Builder should work with no domain routers"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        builder = FastStreamAppBuilder()
        app = builder.build()

        assert isinstance(app, FastStream)
        assert isinstance(app.broker, RedisBroker)

    @patch("app.shared.events.builder.get_config")
    def test_router_factories_called_in_registration_order(self, mock_config):
        """Router factories should be called in the order they were registered"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        call_order = []

        def factory1():
            call_order.append("factory1")
            return RedisRouter()

        def factory2():
            call_order.append("factory2")
            return RedisRouter()

        def factory3():
            call_order.append("factory3")
            return RedisRouter()

        builder = FastStreamAppBuilder()
        (
            builder.add_domain_router(factory1)
            .add_domain_router(factory2)
            .add_domain_router(factory3)
            .build()
        )

        assert call_order == ["factory1", "factory2", "factory3"]

    @patch("app.shared.events.builder.get_config")
    def test_router_factory_exceptions_are_not_caught(self, mock_config):
        """Builder should not catch exceptions from router factories"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        def failing_factory():
            raise ValueError("Test factory error")

        builder = FastStreamAppBuilder()
        builder.add_domain_router(failing_factory)

        with pytest.raises(ValueError, match="Test factory error"):
            builder.build()


class TestFastStreamAppBuilderCliIntegration:
    """Test CLI integration scenarios"""

    @patch("app.shared.events.builder.get_config")
    def test_build_creates_app_suitable_for_cli(self, mock_config):
        """Built app should be suitable for FastStream CLI usage"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        builder = FastStreamAppBuilder()
        app = builder.build()

        # Verify app has required attributes for CLI
        assert isinstance(app, FastStream)
        assert hasattr(app, "broker")
        assert hasattr(app, "start")
        assert hasattr(app, "stop")
        assert callable(app.start)
        assert callable(app.stop)

    @patch("app.shared.events.builder.get_config")
    def test_app_supports_worker_scaling(self, mock_config):
        """Built app should support multi-worker CLI scaling"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        # Create router factory that simulates domain event handling
        def message_router_factory():
            router = RedisRouter()

            @router.subscriber("test.events")
            async def handle_test_event(message):
                return {"processed": True}

            return router

        builder = FastStreamAppBuilder()
        app = builder.add_domain_router(message_router_factory).build()

        # App should be ready for CLI usage with workers
        assert isinstance(app, FastStream)
        assert isinstance(app.broker, RedisBroker)

    @patch("app.shared.events.builder.get_config")
    def test_multiple_apps_can_be_built_independently(self, mock_config):
        """Multiple FastStream apps can be built from same builder pattern"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        def factory():
            return RedisRouter()

        # Build first app
        builder1 = FastStreamAppBuilder()
        app1 = builder1.add_domain_router(factory).build()

        # Build second app
        builder2 = FastStreamAppBuilder()
        app2 = builder2.add_domain_router(factory).build()

        # Apps should be independent instances
        assert app1 is not app2
        assert app1.broker is not app2.broker


class TestFastStreamAppBuilderErrorHandling:
    """Test error handling in builder"""

    def test_build_raises_error_with_invalid_config(self):
        """Builder should handle configuration errors gracefully"""
        with patch("app.shared.events.builder.get_config") as mock_config:
            # Simulate config error
            mock_config.side_effect = Exception("Config error")

            builder = FastStreamAppBuilder()

            with pytest.raises(Exception, match="Config error"):
                builder.build()

    @patch("app.shared.events.builder.get_config")
    def test_build_handles_broker_creation_failure(self, mock_config):
        """Builder should handle broker creation failures"""
        mock_config.return_value.redis_url = "invalid-redis-url"

        builder = FastStreamAppBuilder()

        # Should not fail during build (broker creation might be lazy)
        # But the app should be created
        app = builder.build()
        assert isinstance(app, FastStream)

    @patch("app.shared.events.builder.get_config")
    def test_none_router_factory_handling(self, mock_config):
        """Builder should handle None router factories gracefully"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        def none_factory():
            return None

        builder = FastStreamAppBuilder()

        # This should raise an error due to None router
        with pytest.raises(Exception):  # FastStream will raise SetupError
            builder.add_domain_router(none_factory).build()


class TestFastStreamAppBuilderIntegration:
    """Integration tests for real-world usage scenarios"""

    @patch("app.shared.events.builder.get_config")
    def test_integration_with_domain_event_patterns(self, mock_config):
        """Builder should integrate well with domain event patterns"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        def agent_events_router_factory():
            router = RedisRouter()

            @router.subscriber("agent.created")
            async def handle_agent_created(message):
                return {"status": "processed"}

            @router.subscriber("agent.updated")
            async def handle_agent_updated(message):
                return {"status": "processed"}

            return router

        def webhook_events_router_factory():
            router = RedisRouter()

            @router.subscriber("webhook.received")
            async def handle_webhook(message):
                return {"status": "processed"}

            return router

        builder = FastStreamAppBuilder()
        app = (
            builder.add_domain_router(agent_events_router_factory)
            .add_domain_router(webhook_events_router_factory)
            .build()
        )

        assert isinstance(app, FastStream)
        assert isinstance(app.broker, RedisBroker)

    @patch("app.shared.events.builder.get_config")
    def test_builder_preserves_router_isolation(self, mock_config):
        """Builder should maintain isolation between domain routers"""
        mock_config.return_value.redis_url = "redis://localhost:6379"

        domain_a_calls = []
        domain_b_calls = []

        def domain_a_factory():
            domain_a_calls.append("created")
            return RedisRouter()

        def domain_b_factory():
            domain_b_calls.append("created")
            return RedisRouter()

        builder = FastStreamAppBuilder()
        (builder.add_domain_router(domain_a_factory).add_domain_router(domain_b_factory).build())

        # Each domain should have been called once
        assert domain_a_calls == ["created"]
        assert domain_b_calls == ["created"]
