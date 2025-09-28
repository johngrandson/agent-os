"""Message event subscribers"""

from app.events.core.registry import event_registry
from faststream.redis import RedisRouter

from .events import MessageEventPayload
from .handlers import handle_message_received, handle_message_sent


# Create message-specific router
message_router = RedisRouter()


@message_router.subscriber("messages.message_received")
async def message_received_subscriber(data: MessageEventPayload) -> None:
    """Message received event subscriber"""
    await handle_message_received(data)


@message_router.subscriber("messages.message_sent")
async def message_sent_subscriber(data: MessageEventPayload) -> None:
    """Message sent event subscriber"""
    await handle_message_sent(data)


# Register the router with the event registry
event_registry.register_domain_router("messages", message_router)
