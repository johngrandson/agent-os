"""Tests for EventRegistry router management functionality"""

from unittest.mock import Mock

import pytest
from app.events.core.registry import EventRegistry
from faststream.redis import RedisRouter


class TestEventRegistry:
    """Test EventRegistry router management methods"""

    def setup_method(self):
        """Create fresh registry for each test"""
        self.registry = EventRegistry()

    def test_register_domain_router_stores_router_correctly(self):
        """Test that register_domain_router stores router with correct domain key"""
        # Arrange
        mock_router = Mock(spec=RedisRouter)
        domain = "test_domain"

        # Act
        self.registry.register_domain_router(domain, mock_router)

        # Assert
        assert domain in self.registry._routers
        assert self.registry._routers[domain] is mock_router

    def test_register_domain_router_overwrites_existing_router(self):
        """Test that registering same domain overwrites existing router"""
        # Arrange
        old_router = Mock(spec=RedisRouter)
        new_router = Mock(spec=RedisRouter)
        domain = "test_domain"

        # Act
        self.registry.register_domain_router(domain, old_router)
        self.registry.register_domain_router(domain, new_router)

        # Assert
        assert self.registry._routers[domain] is new_router
        assert self.registry._routers[domain] is not old_router

    def test_get_domain_router_returns_correct_router(self):
        """Test that get_domain_router returns the correct router for domain"""
        # Arrange
        mock_router = Mock(spec=RedisRouter)
        domain = "test_domain"
        self.registry.register_domain_router(domain, mock_router)

        # Act
        result = self.registry.get_domain_router(domain)

        # Assert
        assert result is mock_router

    def test_get_domain_router_raises_error_for_unknown_domain(self):
        """Test that get_domain_router raises ValueError for unknown domain"""
        # Act & Assert
        with pytest.raises(ValueError, match="No router registered for domain: unknown"):
            self.registry.get_domain_router("unknown")

    def test_get_router_is_alias_for_get_domain_router(self):
        """Test that get_router works as alias for get_domain_router"""
        # Arrange
        mock_router = Mock(spec=RedisRouter)
        domain = "test_domain"
        self.registry.register_domain_router(domain, mock_router)

        # Act
        result_direct = self.registry.get_domain_router(domain)
        result_alias = self.registry.get_router(domain)

        # Assert
        assert result_direct is result_alias
        assert result_alias is mock_router

    def test_get_all_routers_returns_copy_of_routers_dict(self):
        """Test that get_all_routers returns a copy, not reference to internal dict"""
        # Arrange
        router1 = Mock(spec=RedisRouter)
        router2 = Mock(spec=RedisRouter)
        self.registry.register_domain_router("domain1", router1)
        self.registry.register_domain_router("domain2", router2)

        # Act
        all_routers = self.registry.get_all_routers()

        # Assert
        assert all_routers is not self.registry._routers  # Should be a copy
        assert all_routers == self.registry._routers  # But contents should be equal
        assert len(all_routers) == 2
        assert all_routers["domain1"] is router1
        assert all_routers["domain2"] is router2

    def test_get_all_routers_returns_router_objects_not_strings(self):
        """Test that get_all_routers().values() returns router objects, not strings"""
        # Arrange
        router1 = Mock(spec=RedisRouter)
        router2 = Mock(spec=RedisRouter)
        router3 = Mock(spec=RedisRouter)

        self.registry.register_domain_router("agent", router1)
        self.registry.register_domain_router("orchestration", router2)
        self.registry.register_domain_router("webhook", router3)

        # Act
        all_routers = self.registry.get_all_routers()
        router_values = list(all_routers.values())

        # Assert
        assert len(router_values) == 3
        for router in router_values:
            assert not isinstance(router, str), f"Expected RedisRouter object, got string: {router}"
            assert isinstance(router, Mock)  # Our mock RedisRouter

    def test_get_all_routers_values_are_actual_router_instances(self):
        """Test that the values from get_all_routers() are the actual router instances"""
        # Arrange
        agent_router = Mock(spec=RedisRouter)
        orchestration_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        # Add unique attributes to identify each router
        agent_router.domain = "agent"
        orchestration_router.domain = "orchestration"
        webhook_router.domain = "webhook"

        self.registry.register_domain_router("agent", agent_router)
        self.registry.register_domain_router("orchestration", orchestration_router)
        self.registry.register_domain_router("webhook", webhook_router)

        # Act
        router_values = list(self.registry.get_all_routers().values())

        # Assert
        domains_found = {router.domain for router in router_values}
        assert domains_found == {"agent", "orchestration", "webhook"}

        # Ensure these are the exact same objects we registered
        assert agent_router in router_values
        assert orchestration_router in router_values
        assert webhook_router in router_values

    def test_empty_registry_returns_empty_dict(self):
        """Test that empty registry returns empty dict from get_all_routers"""
        # Act
        all_routers = self.registry.get_all_routers()

        # Assert
        assert all_routers == {}
        assert len(all_routers) == 0

    def test_multiple_domain_registrations(self):
        """Test registry with multiple domains like actual usage"""
        # Arrange - simulate the actual domains we have
        agent_router = Mock(spec=RedisRouter)
        orchestration_router = Mock(spec=RedisRouter)
        webhook_router = Mock(spec=RedisRouter)

        # Act - register all domains
        self.registry.register_domain_router("agent", agent_router)
        self.registry.register_domain_router("orchestration", orchestration_router)
        self.registry.register_domain_router("webhook", webhook_router)

        # Assert - verify all are accessible
        assert len(self.registry.get_all_routers()) == 3
        assert self.registry.get_router("agent") is agent_router
        assert self.registry.get_router("orchestration") is orchestration_router
        assert self.registry.get_router("webhook") is webhook_router


class TestEventRegistryHandlerManagement:
    """Test EventRegistry handler management functionality"""

    def setup_method(self):
        """Create fresh registry for each test"""
        self.registry = EventRegistry()

    def test_register_handler_stores_handler_correctly(self):
        """Test that register_handler stores handler for channel"""
        # Arrange
        mock_handler = Mock()
        channel = "test_channel"

        # Act
        self.registry.register_handler(channel, mock_handler)

        # Assert
        handlers = self.registry.get_handlers(channel)
        assert len(handlers) == 1
        assert handlers[0] is mock_handler

    def test_register_multiple_handlers_same_channel(self):
        """Test that multiple handlers can be registered for same channel"""
        # Arrange
        handler1 = Mock()
        handler2 = Mock()
        channel = "test_channel"

        # Act
        self.registry.register_handler(channel, handler1)
        self.registry.register_handler(channel, handler2)

        # Assert
        handlers = self.registry.get_handlers(channel)
        assert len(handlers) == 2
        assert handler1 in handlers
        assert handler2 in handlers

    def test_get_handlers_returns_empty_list_for_unknown_channel(self):
        """Test that get_handlers returns empty list for unknown channel"""
        # Act
        handlers = self.registry.get_handlers("unknown_channel")

        # Assert
        assert handlers == []
        assert len(handlers) == 0
