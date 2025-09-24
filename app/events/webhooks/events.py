"""Webhook domain events"""

from dataclasses import dataclass
from typing import Any

from app.events.core.base import BaseEvent


@dataclass
class WebhookEvent(BaseEvent):
    """Webhook-specific event"""

    @classmethod
    def message_received(cls, session_id: str, message_data: dict[str, Any]) -> "WebhookEvent":
        """Create webhook message received event"""
        return cls(entity_id=session_id, event_type="message_received", data=message_data)

    @classmethod
    def message_processed(cls, session_id: str, processing_data: dict[str, Any]) -> "WebhookEvent":
        """Create webhook message processed event"""
        return cls(entity_id=session_id, event_type="message_processed", data=processing_data)

    @classmethod
    def session_status_changed(cls, session_id: str, status_data: dict[str, Any]) -> "WebhookEvent":
        """Create webhook session status changed event"""
        return cls(entity_id=session_id, event_type="session_status_changed", data=status_data)

    @classmethod
    def processing_failed(cls, session_id: str, error_data: dict[str, Any]) -> "WebhookEvent":
        """Create webhook processing failed event"""
        return cls(entity_id=session_id, event_type="processing_failed", data=error_data)

    @classmethod
    def ai_response_generated(
        cls, session_id: str, response_data: dict[str, Any]
    ) -> "WebhookEvent":
        """Create AI response generated event"""
        return cls(entity_id=session_id, event_type="ai_response_generated", data=response_data)

    @classmethod
    def response_sent(cls, session_id: str, sent_data: dict[str, Any]) -> "WebhookEvent":
        """Create response sent event"""
        return cls(entity_id=session_id, event_type="response_sent", data=sent_data)
