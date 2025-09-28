"""Messages domain events"""

from dataclasses import dataclass
from typing import Any

from app.shared.events.base import BaseEvent
from typing_extensions import TypedDict


class MessageEventPayload(TypedDict):
    """Type for message event payloads received by handlers"""

    entity_id: str
    event_type: str
    data: dict[str, Any]


@dataclass
class MessageEvent(BaseEvent):
    """Message-specific event for business message handling"""

    @classmethod
    def message_received(cls, session_id: str, message_data: dict[str, Any]) -> "MessageEvent":
        """Create message received event"""
        return cls(entity_id=session_id, event_type="message_received", data=message_data)

    @classmethod
    def message_sent(cls, session_id: str, message_data: dict[str, Any]) -> "MessageEvent":
        """Create message sent event"""
        return cls(entity_id=session_id, event_type="message_sent", data=message_data)
