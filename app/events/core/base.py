"""Base classes for entity-based event system"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol


logger = logging.getLogger(__name__)


@dataclass
class BaseEvent:
    """Base event class with common fields"""

    entity_id: str
    event_type: str
    data: dict[str, Any]


class EventPublisher(Protocol):
    """Protocol for event publishers"""

    async def publish(self, channel: str, event: BaseEvent) -> None:
        """Publish an event to a specific channel"""
        ...


class BaseEventPublisher(ABC):
    """Abstract base class for domain-specific event publishers"""

    def __init__(self, broker):
        self.broker = broker
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_domain_prefix(self) -> str:
        """Return the domain prefix for event channels (e.g., 'agent', 'webhook')"""
        pass

    def _build_channel(self, event_type: str) -> str:
        """Build channel name with domain prefix"""
        return f"{self.get_domain_prefix()}.{event_type}"

    async def publish(self, channel: str, event: BaseEvent) -> None:
        """Publish an event to the specified channel"""
        try:
            await self.broker.publish(
                {
                    "entity_id": event.entity_id,
                    "event_type": event.event_type,
                    "data": event.data,
                },
                channel=channel,
            )
            self.logger.info(f"Published {event.event_type} event for {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Failed to publish {event.event_type}: {e}")
            raise

    async def publish_domain_event(self, event_type: str, event: BaseEvent) -> None:
        """Publish an event with domain prefix"""
        channel = self._build_channel(event_type)
        await self.publish(channel, event)
