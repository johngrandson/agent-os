"""
Agent domain event classes
"""

from typing import Dict, Any
from app.events.core import BaseEvent, EventPriority
from .types import AgentEventType


class AgentEvent(BaseEvent):
    """Agent-related events"""

    agent_id: str

    @classmethod
    def agent_created(cls, agent_id: str, data: Dict[str, Any] = None) -> "AgentEvent":
        return cls(
            event_type=AgentEventType.AGENT_CREATED,
            agent_id=agent_id,
            data=data or {},
            source="agent_service",
        )

    @classmethod
    def agent_updated(cls, agent_id: str, data: Dict[str, Any] = None) -> "AgentEvent":
        return cls(
            event_type=AgentEventType.AGENT_UPDATED,
            agent_id=agent_id,
            data=data or {},
            source="agent_service",
        )

    @classmethod
    def agent_deleted(cls, agent_id: str, data: Dict[str, Any] = None) -> "AgentEvent":
        return cls(
            event_type=AgentEventType.AGENT_DELETED,
            agent_id=agent_id,
            data=data or {},
            source="agent_service",
        )

    @classmethod
    def agent_activated(cls, agent_id: str) -> "AgentEvent":
        return cls(
            event_type=AgentEventType.AGENT_ACTIVATED,
            agent_id=agent_id,
            source="agent_service",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def agent_deactivated(cls, agent_id: str) -> "AgentEvent":
        return cls(
            event_type=AgentEventType.AGENT_DEACTIVATED,
            agent_id=agent_id,
            source="agent_service",
            priority=EventPriority.HIGH,
        )
