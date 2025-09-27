"""Base classes for entity-based event system"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from core.logger import get_module_logger


logger = get_module_logger(__name__)


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

    def __init__(self, broker) -> None:
        self.broker = broker
        self.logger = get_module_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def get_domain_prefix(self) -> str:
        """Return the domain prefix for event channels (e.g., 'agent', 'webhook')"""

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
            # Use compact logging with emojis for easy identification
            entity_short = event.entity_id[:8]  # First 8 chars for brevity
            action_emoji = {
                "created": "✅",
                "updated": "🔄",
                "deleted": "❌",
                "knowledge_created": "📚",
            }.get(event.event_type, "📤")

            self.logger.info(f"{action_emoji} {event.event_type.upper()} {entity_short}")
        except Exception as e:
            # Provide more specific error messages for common issues
            if "connect()" in str(e):
                self.logger.error(f"❌ BROKER NOT CONNECTED - {event.event_type}")
            else:
                self.logger.error(f"❌ PUBLISH FAILED {event.event_type}: {e}")
            raise

    async def publish_domain_event(self, event_type: str, event: BaseEvent) -> None:
        """Publish an event with domain prefix"""
        channel = self._build_channel(event_type)
        await self.publish(channel, event)
