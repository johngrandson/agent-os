"""
Integration domain event classes
"""

from typing import Dict, Any
from app.events.core import BaseEvent, EventPriority
from .types import IntegrationEventType


class IntegrationEvent(BaseEvent):
    """Integration-related events"""

    integration_id: str

    @classmethod
    def integration_created(
        cls, integration_id: str, data: Dict[str, Any] = None
    ) -> "IntegrationEvent":
        return cls(
            event_type=IntegrationEventType.INTEGRATION_CREATED,
            integration_id=integration_id,
            data=data or {},
            source="integration_service",
            target=integration_id,
            priority=EventPriority.NORMAL,
        )

    @classmethod
    def integration_updated(
        cls, integration_id: str, data: Dict[str, Any] = None
    ) -> "IntegrationEvent":
        return cls(
            event_type=IntegrationEventType.INTEGRATION_UPDATED,
            integration_id=integration_id,
            data=data or {},
            source="integration_service",
            target=integration_id,
            priority=EventPriority.NORMAL,
        )

    @classmethod
    def integration_deleted(
        cls, integration_id: str, data: Dict[str, Any] = None
    ) -> "IntegrationEvent":
        return cls(
            event_type=IntegrationEventType.INTEGRATION_DELETED,
            integration_id=integration_id,
            data=data or {},
            source="integration_service",
            target=integration_id,
            priority=EventPriority.NORMAL,
        )

    @classmethod
    def integration_request(
        cls, integration_id: str, data: Dict[str, Any] = None
    ) -> "IntegrationEvent":
        return cls(
            event_type=IntegrationEventType.INTEGRATION_REQUEST,
            integration_id=integration_id,
            data=data or {},
            source="integration_service",
            target=integration_id,
            priority=EventPriority.LOW,
        )
