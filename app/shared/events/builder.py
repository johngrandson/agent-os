"""FastStream application builder for domain-driven event system"""

from collections.abc import Callable
from typing import Self

from core.config import get_config
from faststream import FastStream
from faststream.redis import RedisBroker, RedisRouter
from faststream.redis.parser import BinaryMessageFormatV1

from .domain_registry import EventRegistry


class FastStreamAppBuilder:
    """Builder for creating FastStream applications with domain registries"""

    def __init__(self) -> None:
        """Initialize builder with empty registry list"""
        self._event_registries: list[EventRegistry] = []
        self._router_factories: list[Callable[[], RedisRouter]] = []

    def add_domain_registry(self, registry: EventRegistry) -> Self:
        """Add domain event registry to the builder

        Args:
            registry: EventRegistry with domain event handlers

        Returns:
            Self for fluent interface
        """
        self._event_registries.append(registry)
        return self

    def add_domain_router(self, router_factory: Callable[[], RedisRouter]) -> Self:
        """Add domain router factory (backward compatibility)

        Args:
            router_factory: Function that returns a configured RedisRouter

        Returns:
            Self for fluent interface
        """
        self._router_factories.append(router_factory)
        return self

    def build(self) -> FastStream:
        """Build the FastStream application with all configured domain registries

        Returns:
            Configured FastStream application ready for CLI usage
        """
        # Create broker with Redis configuration
        broker = self._create_broker()

        # Setup domain registries (new pattern)
        self._setup_domain_registries(broker)

        # Setup domain routers (backward compatibility)
        self._setup_domain_routers(broker)

        # Create and return FastStream app
        return FastStream(broker)

    def _create_broker(self) -> RedisBroker:
        """Create Redis broker with configuration

        Returns:
            Configured RedisBroker instance
        """
        config = get_config()
        return RedisBroker(config.redis_url, message_format=BinaryMessageFormatV1)

    def _setup_domain_registries(self, broker: RedisBroker) -> None:
        """Setup all domain registries on the broker

        Args:
            broker: The RedisBroker to configure with domain registries
        """
        for registry in self._event_registries:
            router = registry.create_router()
            broker.include_router(router)

    def _setup_domain_routers(self, broker: RedisBroker) -> None:
        """Setup all domain routers on the broker (backward compatibility)

        Args:
            broker: The RedisBroker to configure with domain routers
        """
        for router_factory in self._router_factories:
            router = router_factory()
            broker.include_router(router)
