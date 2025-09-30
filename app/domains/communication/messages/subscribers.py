"""Message event subscribers"""

from app.container import Container
from app.shared.events.domain_registry import EventRegistry

from .events import MessageEventPayload
from .handlers import handle_message_received, handle_message_sent


# Create container instance for dependency injection
container = Container()


# Wrap handler with dependencies
async def handle_message_received_with_deps(data: MessageEventPayload) -> None:
    """Wrapper for handle_message_received with dependency injection"""
    webhook_processor = container.webhook_agent_processor()
    waha_client = container.waha_client()

    await handle_message_received(
        data=data,
        webhook_processor=webhook_processor,
        waha_client=waha_client,
    )


# Message domain event registry - declarative configuration
MESSAGE_EVENTS = EventRegistry(
    "messages",
    MessageEventPayload,
    {
        "message_received": handle_message_received_with_deps,
        "message_sent": handle_message_sent,
    },
)
