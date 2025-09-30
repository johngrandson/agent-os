"""Domain Event Registry for declarative subscriber configuration"""

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from faststream.redis import RedisRouter


EventPayloadT = TypeVar("EventPayloadT")
HandlerT = Callable[[EventPayloadT], Awaitable[None]]


class EventRegistry(Generic[EventPayloadT]):
    """Domain event registry for declarative subscriber configuration

    Eliminates boilerplate by providing declarative event-to-handler mappings.
    Follows SOLID principles: Single Responsibility (registry), Open/Closed (extensible).
    """

    def __init__(
        self,
        domain_name: str,
        payload_type: type[EventPayloadT],
        event_handlers: dict[str, HandlerT],
    ) -> None:
        """Initialize domain event registry

        Args:
            domain_name: Domain prefix for event channels (e.g., "agents", "messages")
            payload_type: Type of event payload for type safety
            event_handlers: Mapping of event names to handler functions
        """
        self.domain_name = domain_name
        self.payload_type = payload_type
        self.event_handlers = event_handlers

    def create_router(self) -> RedisRouter:
        """Create FastStream router with all domain event subscribers

        Returns:
            RedisRouter configured with all event handlers for this domain
        """
        router = RedisRouter()

        for event_name, handler in self.event_handlers.items():
            channel = f"{self.domain_name}.{event_name}"
            router.subscriber(channel)(handler)

        return router

    def get_event_names(self) -> list[str]:
        """Get list of all registered event names for this domain"""
        return list(self.event_handlers.keys())

    def get_channels(self) -> list[str]:
        """Get list of all channel names for this domain"""
        return [f"{self.domain_name}.{event_name}" for event_name in self.event_handlers.keys()]
