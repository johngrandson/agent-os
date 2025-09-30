"""Message event subscribers"""

from app.shared.events.domain_registry import EventRegistry

from .events import MessageEventPayload
from .handlers import handle_message_received, handle_message_sent


# Message domain event registry - declarative configuration
MESSAGE_EVENTS = EventRegistry(
    "messages",
    MessageEventPayload,
    {
        "message_received": handle_message_received,
        "message_sent": handle_message_sent,
    },
)
