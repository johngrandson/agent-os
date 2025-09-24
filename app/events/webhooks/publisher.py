"""Webhook event publisher"""

from typing import Any

from app.events.core.base import BaseEventPublisher

from .events import WebhookEvent


class WebhookEventPublisher(BaseEventPublisher):
    """Publisher for webhook domain events"""

    def get_domain_prefix(self) -> str:
        return "webhook"

    async def message_received(self, session_id: str, message_data: dict[str, Any]) -> None:
        """Publish webhook message received event"""
        event = WebhookEvent.message_received(session_id, message_data)
        await self.publish_domain_event("message_received", event)

    async def message_processed(self, session_id: str, processing_data: dict[str, Any]) -> None:
        """Publish webhook message processed event"""
        event = WebhookEvent.message_processed(session_id, processing_data)
        await self.publish_domain_event("message_processed", event)

    async def session_status_changed(self, session_id: str, status_data: dict[str, Any]) -> None:
        """Publish webhook session status changed event"""
        event = WebhookEvent.session_status_changed(session_id, status_data)
        await self.publish_domain_event("session_status_changed", event)

    async def processing_failed(self, session_id: str, error_data: dict[str, Any]) -> None:
        """Publish webhook processing failed event"""
        event = WebhookEvent.processing_failed(session_id, error_data)
        await self.publish_domain_event("processing_failed", event)

    async def ai_response_generated(self, session_id: str, response_data: dict[str, Any]) -> None:
        """Publish AI response generated event"""
        event = WebhookEvent.ai_response_generated(session_id, response_data)
        await self.publish_domain_event("ai_response_generated", event)

    async def response_sent(self, session_id: str, sent_data: dict[str, Any]) -> None:
        """Publish response sent event"""
        event = WebhookEvent.response_sent(session_id, sent_data)
        await self.publish_domain_event("response_sent", event)
