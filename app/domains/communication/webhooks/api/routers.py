"""WhatsApp webhook API routers"""

import asyncio
import random

from app.container import Container
from app.domains.communication.webhooks.api.schemas import WebhookData
from app.domains.communication.webhooks.services.webhook_agent_processor import (
    WebhookAgentProcessor,
)
from app.infrastructure.external.waha.client import WahaClient
from core.config import get_config
from core.logger import get_module_logger
from dependency_injector.wiring import Provide, inject

from fastapi import APIRouter, Depends, HTTPException, status


logger = get_module_logger(__name__)

webhook_router = APIRouter()
webhook_router.tags = ["API Webhooks"]


@webhook_router.post(
    "/waha",
    response_model=None,
    status_code=200,
    summary="Handle WhatsApp webhook",
    description="Process WhatsApp messages and respond directly",
)
@inject
async def handle_whatsapp_webhook(
    webhook_data: WebhookData,
    webhook_processor: WebhookAgentProcessor = Depends(Provide[Container.webhook_agent_processor]),
    waha_client: WahaClient = Depends(Provide[Container.waha_client]),
) -> dict[str, str]:
    """Simple webhook handler - process messages directly"""
    try:
        logger.info(f"Received webhook event: {webhook_data.event}")

        # Only process message events
        if not webhook_data.is_message_event():
            logger.debug(f"Ignoring non-message event: {webhook_data.event}")
            return {"status": "success", "message": "Event acknowledged"}

        # Extract required data
        chat_id = webhook_data.get_chat_id()
        message_body = webhook_data.get_message_body()
        agent_id = webhook_data.get_agent_id()

        # Debug: Log full webhook data
        logger.info(f"Webhook payload: {webhook_data.model_dump()}")

        if not chat_id or not agent_id:
            logger.warning(f"Missing critical fields: chat_id={chat_id}, agent_id={agent_id}")
            return {"status": "success", "message": "Missing critical fields"}

        if not message_body or not message_body.strip():
            logger.info(f"Empty message from {chat_id}, ignoring")
            return {"status": "success", "message": "Empty message ignored"}

        # Human-like interaction flow to avoid blocking
        await _human_like_response_flow(
            webhook_processor, waha_client, agent_id, message_body, chat_id
        )

        return {"status": "success", "message": "Message processed"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook",
        ) from e


async def _human_like_response_flow(
    webhook_processor: WebhookAgentProcessor,
    waha_client: WahaClient,
    agent_id: str,
    message_body: str,
    chat_id: str,
) -> None:
    """
    Implement human-like response flow to avoid WhatsApp blocking:
    1. Send seen status
    2. Start typing indicator
    3. Random delay while processing
    4. Stop typing
    5. Send response
    """
    config = get_config()

    try:
        # Step 1: Mark message as seen (immediate)
        await waha_client.send_seen_status(chat_id)

        # Step 2: Start typing indicator
        await waha_client.start_typing(chat_id)

        # Step 3: Random delay to simulate human thinking time
        delay = random.randint(config.WHATSAPP_MIN_DELAY_SECONDS, config.WHATSAPP_MAX_DELAY_SECONDS)
        logger.info(f"💭 Simulating human thinking time: {delay}s for {chat_id}")

        # Process message during the delay (but don't block the delay)
        async def process_message() -> str | None:
            return await webhook_processor.process_message(agent_id, message_body, chat_id)

        # Run processing and delay concurrently
        response_task = asyncio.create_task(process_message())
        delay_task = asyncio.create_task(asyncio.sleep(delay))

        # Wait for both to complete
        response, _ = await asyncio.gather(response_task, delay_task)

        # Step 4: Show typing for a bit longer, then stop
        await asyncio.sleep(config.WHATSAPP_TYPING_DURATION_SECONDS)
        await waha_client.stop_typing(chat_id)

        # Step 5: Send response if we got one
        if response:
            success = await waha_client.send_text_message(chat_id, response)
            if success:
                logger.info(f"✅ Human-like WhatsApp conversation completed: {chat_id}")
            else:
                logger.error(f"❌ Failed to send WhatsApp response: {chat_id}")
        else:
            logger.info(f"⚠️ No response generated for {chat_id}")

    except Exception as e:
        logger.error(f"Error in human-like response flow for {chat_id}: {e}")
        # Always try to stop typing if something goes wrong
        try:
            await waha_client.stop_typing(chat_id)
        except Exception:
            pass  # Ignore errors when cleaning up
