"""Message event handlers - Pure business logic"""

from app.events.broker import broker
from core.logger import get_module_logger

from .events import MessageEventPayload
from .publisher import MessageEventPublisher


logger = get_module_logger(__name__)

# Create message publisher for use in handlers if needed
message_publisher = MessageEventPublisher(broker=broker)


async def handle_message_received(data: MessageEventPayload) -> None:
    """Handle message received events"""
    session_id = data["entity_id"]
    message_data = data["data"]

    logger.info(f"Message received for session: {session_id}")

    # Extract message content for logging
    message_content = message_data.get("message_content", "")
    if message_content:
        # Log first 100 chars for debugging
        content_preview = message_content[:100]
        logger.debug(f"Message content: {content_preview}")

    # Log other relevant data
    user_id = message_data.get("user_id")
    chat_id = message_data.get("chat_id")

    if user_id:
        logger.debug(f"Message from user: {user_id}")
    if chat_id:
        logger.debug(f"Message in chat: {chat_id}")


async def handle_message_sent(data: MessageEventPayload) -> None:
    """Handle message sent events"""
    session_id = data["entity_id"]
    message_data = data["data"]

    logger.info(f"Message sent for session: {session_id}")

    # Extract message content for logging
    message_content = message_data.get("message_content", "")
    if message_content:
        # Log first 100 chars for debugging
        content_preview = message_content[:100]
        logger.debug(f"Sent message content: {content_preview}")

    # Log other relevant data
    agent_id = message_data.get("agent_id")
    chat_id = message_data.get("chat_id")
    delivery_status = message_data.get("delivery_status")

    if agent_id:
        logger.debug(f"Message from agent: {agent_id}")
    if chat_id:
        logger.debug(f"Message sent to chat: {chat_id}")
    if delivery_status:
        logger.debug(f"Delivery status: {delivery_status}")
