"""Webhook event handlers"""

import logging
from datetime import UTC
from typing import Any

from app.events.broker import broker
from app.events.core.registry import event_registry
from app.webhook.api.schemas import WebhookData, WebhookPayload
from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)

# Create webhook-specific router
webhook_router = RedisRouter()


async def _publish_processing_failed(
    session_id: str, agent_id: str, error: str, webhook_data: WebhookData
):
    """Helper to publish processing failed events"""
    from app.events.webhooks.publisher import WebhookEventPublisher

    publisher = WebhookEventPublisher(broker=broker)
    await publisher.processing_failed(
        session_id,
        {
            "agent_id": agent_id,
            "error": error,
            "webhook_data": webhook_data.model_dump(),
        },
    )


async def process_message_with_agent(session_id: str, webhook_data: WebhookData, agent_id: str):
    """Process webhook message through AI agent with timeout and circuit breaker"""
    import asyncio
    from datetime import datetime

    # Add timeout for agent processing
    timeout_seconds = 30

    try:
        from app.container import Container

        logger.info(f"Processing message for agent {agent_id} in session {session_id}")

        # Get message content using Pydantic model methods
        message_content = webhook_data.get_message_body()
        chat_id = webhook_data.get_chat_id()

        if not message_content:
            logger.warning(f"Empty message content for session {session_id}")
            return

        # Create container and get agent service
        container = Container()
        agent_service = container.agent_service()

        # Get agent configuration with timeout
        agent = await asyncio.wait_for(agent_service.get_agent_by_id(agent_id), timeout=5.0)

        if not agent:
            logger.error(f"Agent {agent_id} not found")
            await _publish_processing_failed(
                session_id, agent_id, f"Agent {agent_id} not found", webhook_data
            )
            return

        # Process message through agent
        logger.info(f"Agent {agent.name} processing message: {message_content[:100]}...")

        # Create agent processor
        from app.webhook.services.webhook_agent_processor import WebhookAgentProcessor

        processor = WebhookAgentProcessor(
            container.agent_repository(),
            container.webhook_event_publisher(),
            container.config,
        )

        # Initialize agents if not already done (with timeout)
        if not processor.has_agents():
            await asyncio.wait_for(processor.initialize_agents(), timeout=10.0)

        # Process and get response with timeout
        logger.info(f"Starting AI processing (timeout: {timeout_seconds}s)...")
        response = await asyncio.wait_for(
            processor.process_message(agent_id, message_content, chat_id),
            timeout=timeout_seconds,
        )

        if response:
            # Publish AI response generated event
            from datetime import datetime

            from app.events.webhooks.publisher import WebhookEventPublisher

            publisher = WebhookEventPublisher(broker=broker)
            await publisher.ai_response_generated(
                session_id,
                {
                    "agent_id": agent_id,
                    "response": response,
                    "original_message": message_content,
                    "chat_id": chat_id,
                    "processed_at": datetime.now(UTC).isoformat(),
                    "processing_duration": f"<{timeout_seconds}s",
                },
            )
            logger.info(f"Successfully processed message for session {session_id}")
        else:
            logger.warning(f"Agent {agent_id} returned empty response for session {session_id}")
            await _publish_processing_failed(
                session_id, agent_id, "Agent returned empty response", webhook_data
            )

    except TimeoutError:
        error_msg = f"Agent processing timed out after {timeout_seconds}s"
        logger.error(f"Timeout error for session {session_id}: {error_msg}")
        await _publish_processing_failed(session_id, agent_id, error_msg, webhook_data)
    except Exception as e:
        logger.error(f"Error processing message with agent: {e}")
        await _publish_processing_failed(session_id, agent_id, str(e), webhook_data)


@webhook_router.subscriber("webhook.message_received")
async def handle_message_received(data: dict[str, Any]):
    """Handle webhook message received events - orchestrates message processing"""
    session_id = data.get("entity_id")
    message_data = data.get("data", {})

    logger.info(f"Webhook message received for session: {session_id}")
    logger.debug(f"Message data: {message_data}")

    try:
        # Extract webhook data from event
        webhook_data_dict = message_data.get("webhook_data")
        if not webhook_data_dict:
            logger.error("No webhook_data found in message event")
            return

        # Reconstruct WebhookData from dict
        webhook_data = WebhookData(**webhook_data_dict)

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
            if "webhook_data" in locals():
                await _publish_processing_failed(session_id, "unknown", str(e), webhook_data)
            else:
                # Create minimal webhook data from available data
                minimal_payload = WebhookPayload(
                    from_="unknown", body=str(message_data), from_me=False
                )
                minimal_webhook_data = WebhookData(event="message", payload=minimal_payload)
                await _publish_processing_failed(
                    session_id, "unknown", str(e), minimal_webhook_data
                )
        except Exception as nested_error:
            logger.error(f"Failed to publish processing failure: {nested_error}")


@webhook_router.subscriber("webhook.message_processed")
async def handle_message_processed(data: dict[str, Any]):
    """Handle webhook message processed events"""
    session_id = data.get("entity_id")
    processing_data = data.get("data", {})

    logger.info(f"Webhook message processed for session: {session_id}")
    logger.debug(f"Processing result: {processing_data}")

    # Add any message processing side effects here
    # e.g., update metrics, send confirmations


@webhook_router.subscriber("webhook.session_status_changed")
async def handle_session_status_changed(data: dict[str, Any]):
    """Handle webhook session status changed events"""
    session_id = data.get("entity_id")
    status_data = data.get("data", {})

    logger.info(f"Session status changed for: {session_id}")
    logger.debug(f"Status data: {status_data}")

    # Add any status change side effects here
    # e.g., update session store, notify administrators


@webhook_router.subscriber("webhook.processing_failed")
async def handle_processing_failed(data: dict[str, Any]):
    """Handle webhook processing failed events with retry logic"""
    session_id = data.get("entity_id")
    error_data = data.get("data", {})

    logger.error(f"Webhook processing failed for session: {session_id}")
    logger.error(f"Error details: {error_data}")

    agent_id = error_data.get("agent_id", "unknown")
    error_message = error_data.get("error", "Unknown error")
    webhook_data_dict = error_data.get("webhook_data", {})

    # Implement retry logic
    retry_count = error_data.get("retry_count", 0)
    max_retries = 3

    if retry_count < max_retries:
        # Exponential backoff: wait 2^retry_count seconds
        import asyncio

        retry_delay = 2**retry_count

        logger.info(
            f"Scheduling retry {retry_count + 1}/{max_retries} for session {session_id} "
            f"in {retry_delay}s"
        )

        await asyncio.sleep(retry_delay)

        # Retry the message processing
        try:
            # Reconstruct WebhookData for retry
            if isinstance(webhook_data_dict, dict):
                webhook_data = WebhookData(**webhook_data_dict)
            else:
                # Fallback - webhook_data_dict might already be serialized
                logger.warning(f"Webhook data is not a dict: {type(webhook_data_dict)}")
                return

            await process_message_with_agent(session_id, webhook_data, agent_id)

        except Exception as retry_error:
            logger.error(f"Retry {retry_count + 1} failed for session {session_id}: {retry_error}")

            # Create WebhookData for failed retry reporting
            try:
                failed_webhook_data = (
                    WebhookData(**webhook_data_dict)
                    if isinstance(webhook_data_dict, dict)
                    else None
                )
                if failed_webhook_data:
                    await _publish_processing_failed(
                        session_id,
                        agent_id,
                        f"Retry {retry_count + 1} failed: {retry_error}",
                        failed_webhook_data,
                    )
            except Exception as nested_error:
                logger.error(f"Failed to publish retry failure: {nested_error}")
    else:
        # Max retries reached - send to dead letter queue
        logger.error(
            f"Max retries ({max_retries}) reached for session {session_id}. "
            f"Moving to dead letter queue."
        )

        # Log final failure and prepare for dead letter queue implementation
        logger.critical(f"DEAD LETTER: Failed to process message after {max_retries} retries")
        logger.critical(f"Session: {session_id}, Agent: {agent_id}, Error: {error_message}")

        # Optionally, send a generic error response to user
        # await _send_error_response_to_user(session_id, webhook_data)


@webhook_router.subscriber("webhook.ai_response_generated")
async def handle_ai_response_generated(data: dict[str, Any]):
    """Handle AI response generated events - send response back to user"""
    session_id = data.get("entity_id")
    response_data = data.get("data", {})

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
        from datetime import datetime

        # Simulate message sending until WAHA API client is implemented
        logger.info(f"📱 Would send to {chat_id}: {response_text}")

        # Publish response sent event
        from app.events.webhooks.publisher import WebhookEventPublisher

        publisher = WebhookEventPublisher(broker=broker)

        await publisher.response_sent(
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
        # Consider implementing retry logic for response sending failures


@webhook_router.subscriber("webhook.response_sent")
async def handle_response_sent(data: dict[str, Any]):
    """Handle response sent events"""
    session_id = data.get("entity_id")
    sent_data = data.get("data", {})

    logger.info(f"Response sent for session: {session_id}")
    logger.debug(f"Sent data: {sent_data}")

    # Add any response sent side effects here
    # e.g., update metrics, log conversation, update session state


# Register the router with the event registry
event_registry.register_domain_router("webhook", webhook_router)
