"""WhatsApp webhook API routers"""

from app.container import Container
from app.domains.communication.messages.publisher import MessageEventPublisher
from app.domains.communication.webhooks.api.schemas import WebhookData
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
    description="""
    Handle incoming WhatsApp webhook events using event-driven architecture.

    Supported events:
    - message: Incoming messages from WhatsApp
    - session.status: Session status updates

    Required fields:
    - event: Event type
    - metadata: Event metadata containing agent.id
    - payload: Event payload data

    Returns:
    Success status
    """,
)
@inject
async def handle_whatsapp_webhook(
    webhook_data: WebhookData,
    message_publisher: MessageEventPublisher = Depends(Provide[Container.message_event_publisher]),
) -> dict[str, str]:
    """Lightweight webhook handler - validates and publishes events"""
    try:
        logger.info(f"Received webhook event: {webhook_data.event}")

        # Determine session ID from webhook data
        session_id = _extract_session_id(webhook_data)

        # Serialize webhook data once
        webhook_data_dict = webhook_data.model_dump()

        # Handle different event types
        if webhook_data.event == "message":
            await message_publisher.message_received(
                session_id, {"webhook_data": webhook_data_dict}
            )
        elif webhook_data.event == "session.status":
            # For session status events, we'll still use message_received but with different data
            await message_publisher.message_received(
                session_id,
                {
                    "event_type": "session_status",
                    "status": webhook_data.payload,
                    "webhook_data": webhook_data_dict,
                },
            )
        else:
            logger.info(f"Unhandled event type: {webhook_data.event}")

        return {"status": "success", "message": "Webhook event published"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook",
        ) from e


def _extract_session_id(webhook_data: WebhookData) -> str:
    """Extract session ID from webhook data"""
    agent_id = webhook_data.get_agent_id()
    if agent_id:
        return f"session_{agent_id}"
    return "default_session"
