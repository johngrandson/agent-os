"""Event registry for managing handlers and publishers"""

import logging
from typing import Any, Callable, Dict, List

from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)


class EventRegistry:
    """Registry for managing event handlers across different domains"""

    def __init__(self):
        self._routers: Dict[str, RedisRouter] = {}
        self._handlers: Dict[str, List[Callable]] = {}

    def register_domain_router(self, domain: str, router: RedisRouter) -> None:
        """Register a domain-specific router"""
        self._routers[domain] = router
        logger.info(f"Registered {domain} event router")

    def get_domain_router(self, domain: str) -> RedisRouter:
        """Get router for a specific domain"""
        if domain not in self._routers:
            raise ValueError(f"No router registered for domain: {domain}")
        return self._routers[domain]

    def get_all_routers(self) -> List[RedisRouter]:
        """Get all registered routers"""
        return list(self._routers.values())

    def register_handler(self, channel: str, handler: Callable) -> None:
        """Register a handler for a specific channel"""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        logger.info(f"Registered handler for channel: {channel}")

    def get_handlers(self, channel: str) -> List[Callable]:
        """Get all handlers for a channel"""
        return self._handlers.get(channel, [])


# Global event registry instance
event_registry = EventRegistry()
