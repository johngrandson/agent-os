"""Message event handlers - Pure business logic"""

from typing import TYPE_CHECKING

from app.shared.events.broker import broker
from core.logger import get_module_logger

from .events import MessageEventPayload
from .publisher import MessageEventPublisher


if TYPE_CHECKING:
    from app.domains.communication.webhooks.services.webhook_agent_processor import (
        WebhookAgentProcessor,
    )
    from app.infrastructure.external.waha.client import WahaClient

logger = get_module_logger(__name__)

# Create message publisher for use in handlers if needed
message_publisher = MessageEventPublisher(broker=broker)

# Global webhook processor instance (will be injected)
_webhook_processor: "WebhookAgentProcessor | None" = None

# Global WAHA client instance (will be injected)
_waha_client: "WahaClient | None" = None


def set_webhook_processor(processor: "WebhookAgentProcessor") -> None:
    """Set the webhook processor for message handling."""
    global _webhook_processor
    _webhook_processor = processor


def set_waha_client(client: "WahaClient") -> None:
    """Set the WAHA client for sending WhatsApp messages."""
    global _waha_client
    _waha_client = client


async def handle_message_received(data: MessageEventPayload) -> None:
    """Handle message received events and process with webhook agent"""
    session_id = data["entity_id"]
    message_data = data["data"]

    logger.info(f"Message received for session: {session_id}")

    # Extract webhook data if available
    webhook_data = message_data.get("webhook_data")
    if not webhook_data:
        logger.warning("No webhook_data found in message event")
        return

    # Extract required fields from webhook data
    try:
        payload = webhook_data.get("payload", {})
        metadata = webhook_data.get("metadata", {})

        chat_id = payload.get("chat_id")  # WhatsApp sender number
        message_body = payload.get("body")  # Message text
        agent_id = metadata.get("agent_id") if metadata else None

        logger.debug(f"Extracted: chat_id={chat_id}, message='{message_body}', agent_id={agent_id}")

        # Validate required fields
        if not chat_id or not message_body:
            logger.warning(
                f"Missing required fields: chat_id={chat_id}, message_body={message_body}"
            )
            return

        if not agent_id:
            logger.warning("No agent_id found in webhook metadata")
            return

        # Process message with webhook processor
        if _webhook_processor:
            logger.info(f"Processing message with agent {agent_id}")
            response = await _webhook_processor.process_message(agent_id, message_body, chat_id)

            if response:
                logger.info(f"Agent responded: {response[:100]}...")

                # Send response back to WhatsApp via WAHA API
                if _waha_client:
                    success = await _waha_client.send_text_message(chat_id, response)
                    if success:
                        logger.info(f"Response sent to WhatsApp chat: {chat_id}")
                    else:
                        logger.error(f"Failed to send response to WhatsApp chat: {chat_id}")
                else:
                    logger.error("WAHA client not initialized - cannot send WhatsApp message")
            else:
                logger.info("Agent did not provide a response")
        else:
            logger.error("Webhook processor not initialized - cannot process message")

    except Exception as e:
        logger.error(f"Error processing webhook message: {e}")
        logger.exception("Full traceback:")


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
