"""Webhook event handlers"""

import asyncio
import logging
from datetime import UTC, datetime

from app.events.broker import broker
from app.events.core.registry import event_registry
from app.events.webhooks.events import WebhookEventPayload
from app.events.webhooks.publisher import WebhookEventPublisher
from app.webhook.api.schemas import WebhookData, WebhookPayload
from core.config import config
from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)

# Create webhook-specific router and publisher
webhook_router = RedisRouter()
webhook_publisher = WebhookEventPublisher(broker=broker)


async def _safe_reconstruct_webhook_data(webhook_data_dict: dict | None) -> WebhookData | None:
    """Safely reconstruct WebhookData from dict with clear error handling"""
    if not webhook_data_dict or not isinstance(webhook_data_dict, dict):
        logger.error(f"Invalid webhook data dict: {type(webhook_data_dict)}")
        return None

    try:
        return WebhookData(**webhook_data_dict)
    except Exception as e:
        logger.error(f"Failed to reconstruct WebhookData: {e}")
        return None


async def _setup_agent_processor(agent_id: str):
    """Setup agent processor and get agent configuration"""
    from app.container import Container
    from app.webhook.services.webhook_agent_processor import WebhookAgentProcessor

    container = Container()
    agent_service = container.agent_service()

    # Get agent with timeout
    agent = await asyncio.wait_for(
        agent_service.get_agent_by_id(agent_id=agent_id), timeout=config.AGENT_GET_TIMEOUT
    )

    if not agent:
        msg = f"Agent {agent_id} not found"
        raise ValueError(msg)

    print(f"#################### Agent found: {container}")

    # Create processor
    processor = WebhookAgentProcessor(
        container.agent_cache(),
        container.webhook_event_publisher(),
    )

    return processor, agent


async def _publish_ai_response(
    session_id: str, agent_id: str, response: str, message_content: str, chat_id: str
):
    """Publish AI response generated event"""
    await webhook_publisher.ai_response_generated(
        session_id,
        {
            "agent_id": agent_id,
            "response": response,
            "original_message": message_content,
            "chat_id": chat_id,
            "processed_at": datetime.now(UTC).isoformat(),
            "processing_duration": f"<{config.AGENT_PROCESSING_TIMEOUT}s",
        },
    )


async def _publish_processing_failed(
    session_id: str, agent_id: str, error: str, webhook_data: WebhookData
):
    """Helper to publish processing failed events"""
    await webhook_publisher.processing_failed(
        session_id,
        {
            "agent_id": agent_id,
            "error": error,
            "webhook_data": webhook_data.model_dump(),
        },
    )


async def process_message_with_agent(session_id: str, webhook_data: WebhookData, agent_id: str):
    """Process webhook message through AI agent - simplified orchestration"""
    try:
        logger.info(f"Processing message for agent {agent_id} in session {session_id}")

        # Validate input
        message_content = webhook_data.get_message_body()
        if not message_content:
            logger.warning(f"Empty message content for session {session_id}")
            return

        chat_id = webhook_data.get_chat_id()

        # Setup agent and processor
        processor, agent = await _setup_agent_processor(agent_id)
        logger.info(f"Agent {agent.name} processing message: {message_content[:100]}...")

        # Process message with timeout
        logger.info(f"Starting AI processing (timeout: {config.AGENT_PROCESSING_TIMEOUT}s)...")
        response = await asyncio.wait_for(
            processor.process_message(agent_id, message_content, chat_id),
            timeout=config.AGENT_PROCESSING_TIMEOUT,
        )

        # Handle response
        if response:
            await _publish_ai_response(session_id, agent_id, response, message_content, chat_id)
            logger.info(f"Successfully processed message for session {session_id}")
        else:
            logger.warning(f"Agent {agent_id} returned empty response for session {session_id}")
            await _publish_processing_failed(
                session_id, agent_id, "Agent returned empty response", webhook_data
            )

    except TimeoutError:
        error_msg = f"Agent processing timed out after {config.AGENT_PROCESSING_TIMEOUT}s"
        logger.error(f"Timeout error for session {session_id}: {error_msg}")
        await _publish_processing_failed(session_id, agent_id, error_msg, webhook_data)
    except ValueError as e:  # Agent not found
        logger.error(f"Agent error for session {session_id}: {e}")
        await _publish_processing_failed(session_id, agent_id, str(e), webhook_data)
    except Exception as e:
        logger.error(f"Error processing message with agent: {e}")
        await _publish_processing_failed(session_id, agent_id, str(e), webhook_data)


@webhook_router.subscriber("webhook.message_received")
async def handle_message_received(data: WebhookEventPayload):
    """Handle webhook message received events - orchestrates message processing"""
    session_id = data["entity_id"]
    message_data = data["data"]

    logger.info(f"Webhook message received for session: {session_id}")
    logger.debug(f"Message data: {message_data}")

    try:
        # Extract webhook data from event
        webhook_data_dict = message_data.get("webhook_data")
        if not webhook_data_dict:
            logger.error("No webhook_data found in message event")
            return

        # Reconstruct WebhookData from dict
        webhook_data = await _safe_reconstruct_webhook_data(webhook_data_dict)
        if not webhook_data:
            return

        # Get agent ID using Pydantic model method
        agent_id = webhook_data.get_agent_id()
        if not agent_id:
            logger.error("No agent ID found in webhook metadata")
            return

        # Process the message through AI agent
        await process_message_with_agent(session_id, webhook_data, agent_id)

    except Exception as e:
        logger.error(f"Error handling message received event: {e}")
        # Create a minimal WebhookData for error reporting
        try:
            if "webhook_data" in locals() and webhook_data is not None:
                await _publish_processing_failed(session_id, "unknown", str(e), webhook_data)
            else:
                # Create minimal webhook data from available data
                minimal_payload = WebhookPayload.model_validate(
                    {"from": "unknown", "body": str(message_data), "fromMe": False}
                )
                minimal_webhook_data = WebhookData(
                    event="message", payload=minimal_payload, metadata=None
                )
                await _publish_processing_failed(
                    session_id, "unknown", str(e), minimal_webhook_data
                )
        except Exception as nested_error:
            logger.error(f"Failed to publish processing failure: {nested_error}")


@webhook_router.subscriber("webhook.message_processed")
async def handle_message_processed(data: WebhookEventPayload):
    """Handle webhook message processed events"""
    session_id = data["entity_id"]
    processing_data = data["data"]

    logger.info(f"Webhook message processed for session: {session_id}")
    logger.debug(f"Processing result: {processing_data}")


@webhook_router.subscriber("webhook.session_status_changed")
async def handle_session_status_changed(data: WebhookEventPayload):
    """Handle webhook session status changed events"""
    session_id = data["entity_id"]
    status_data = data["data"]

    logger.info(f"Session status changed for: {session_id}")
    logger.debug(f"Status data: {status_data}")


async def _attempt_message_retry(session_id: str, webhook_data_dict: dict, agent_id: str) -> bool:
    """Attempt to retry message processing. Returns True if successful."""
    try:
        # Reconstruct WebhookData for retry
        webhook_data = await _safe_reconstruct_webhook_data(webhook_data_dict)
        if not webhook_data:
            logger.error(f"Cannot reconstruct webhook data for retry in session {session_id}")
            return False

        await process_message_with_agent(session_id, webhook_data, agent_id)
        return True

    except Exception as retry_error:
        logger.error(f"Retry failed for session {session_id}: {retry_error}")

        # Report retry failure
        failed_webhook_data = await _safe_reconstruct_webhook_data(webhook_data_dict)
        if failed_webhook_data:
            await _publish_processing_failed(
                session_id,
                agent_id,
                f"Retry failed: {retry_error}",
                failed_webhook_data,
            )
        return False


async def _handle_max_retries_reached(session_id: str, agent_id: str, error_message: str):
    """Handle case when max retries have been reached"""
    logger.error(
        f"Max retries ({config.WEBHOOK_MAX_RETRIES}) reached for session {session_id}. "
        "Moving to dead letter queue."
    )
    logger.critical(
        f"DEAD LETTER: Failed to process message after {config.WEBHOOK_MAX_RETRIES} retries"
    )
    logger.critical(f"Session: {session_id}, Agent: {agent_id}, Error: {error_message}")


@webhook_router.subscriber("webhook.processing_failed")
async def handle_processing_failed(data: WebhookEventPayload):
    """Handle webhook processing failed events with simplified retry logic"""
    session_id = data["entity_id"]
    error_data = data["data"]

    logger.error(f"Webhook processing failed for session: {session_id}")
    logger.error(f"Error details: {error_data}")

    agent_id = error_data.get("agent_id", "unknown")
    error_message = error_data.get("error", "Unknown error")
    webhook_data_dict = error_data.get("webhook_data", {})
    retry_count = error_data.get("retry_count", 0)

    if retry_count < config.WEBHOOK_MAX_RETRIES:
        # Exponential backoff
        retry_delay = 2**retry_count
        logger.info(
            f"Scheduling retry {retry_count + 1}/{config.WEBHOOK_MAX_RETRIES} "
            f"for session {session_id} "
            f"in {retry_delay}s"
        )

        await asyncio.sleep(retry_delay)
        await _attempt_message_retry(session_id, webhook_data_dict, agent_id)
    else:
        await _handle_max_retries_reached(session_id, agent_id, error_message)


@webhook_router.subscriber("webhook.ai_response_generated")
async def handle_ai_response_generated(data: WebhookEventPayload):
    """Handle AI response generated events - send response back to user"""
    session_id = data["entity_id"]
    response_data = data["data"]

    logger.info(f"AI response generated for session: {session_id}")
    logger.debug(f"Response data: {response_data}")

    try:
        response_text = response_data.get("response", "")
        agent_id = response_data.get("agent_id")
        chat_id = response_data.get("chat_id", "")

        if not response_text:
            logger.warning(f"Empty response generated for session {session_id}")
            return

        logger.info(f"Sending response to chat {chat_id}: {response_text[:100]}...")

        # Send response via WhatsApp API
        # Simulate message sending until WAHA API client is implemented
        logger.info(f"📱 Would send to {chat_id}: {response_text}")

        # Publish response sent event
        await webhook_publisher.response_sent(
            session_id,
            {
                "agent_id": agent_id,
                "response": response_text,
                "chat_id": chat_id,
                "sent_at": datetime.now(UTC).isoformat(),
                "delivery_status": "sent",  # Real implementation: "sent" | "delivered" | "failed"
            },
        )

    except Exception as e:
        logger.error(f"Error handling AI response generated event: {e}")


@webhook_router.subscriber("webhook.response_sent")
async def handle_response_sent(data: WebhookEventPayload):
    """Handle response sent events"""
    session_id = data["entity_id"]
    sent_data = data["data"]

    logger.info(f"Response sent for session: {session_id}")
    logger.debug(f"Sent data: {sent_data}")


# Register the router with the event registry
event_registry.register_domain_router("webhook", webhook_router)
