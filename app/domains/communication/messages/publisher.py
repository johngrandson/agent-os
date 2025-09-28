"""Message event publisher"""

from typing import Any

from app.shared.events.base import BaseEventPublisher

from .events import MessageEvent


class MessageEventPublisher(BaseEventPublisher):
    """Publisher for messages domain events"""

    def get_domain_prefix(self) -> str:
        return "messages"

    async def message_received(self, session_id: str, message_data: dict[str, Any]) -> None:
        """Publish message received event"""
        event = MessageEvent.message_received(session_id, message_data)
        await self.publish_domain_event("message_received", event)

    async def message_sent(self, session_id: str, message_data: dict[str, Any]) -> None:
        """Publish message sent event"""
        event = MessageEvent.message_sent(session_id, message_data)
        await self.publish_domain_event("message_sent", event)
