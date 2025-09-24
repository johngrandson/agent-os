"""Event registry for managing handlers and publishers"""

import logging
from collections.abc import Callable

from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)


class EventRegistry:
    """Registry for managing event handlers across different domains"""

    def __init__(self):
        self._routers: dict[str, RedisRouter] = {}
        self._handlers: dict[str, list[Callable]] = {}

    def register_domain_router(self, domain: str, router: RedisRouter) -> None:
        """Register a domain-specific router"""
        self._routers[domain] = router
        logger.info(f"Registered {domain} event router")

    def get_domain_router(self, domain: str) -> RedisRouter:
        """Get router for a specific domain"""
        if domain not in self._routers:
            msg = f"No router registered for domain: {domain}"
            raise ValueError(msg)
        return self._routers[domain]

    def get_all_routers(self) -> list[RedisRouter]:
        """Get all registered routers"""
        return list(self._routers.values())

    def register_handler(self, channel: str, handler: Callable) -> None:
        """Register a handler for a specific channel"""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        logger.info(f"Registered handler for channel: {channel}")

    def get_handlers(self, channel: str) -> list[Callable]:
        """Get all handlers for a channel"""
        return self._handlers.get(channel, [])


# Global event registry instance
event_registry = EventRegistry()
