"""Agent domain events"""

from dataclasses import dataclass
from typing import Any, Dict

from app.events.core.base import BaseEvent


@dataclass
class AgentEvent(BaseEvent):
    """Agent-specific event"""

    @classmethod
    def created(cls, agent_id: str, agent_data: Dict[str, Any]) -> "AgentEvent":
        """Create agent created event"""
        return cls(entity_id=agent_id, event_type="created", data=agent_data)

    @classmethod
    def updated(cls, agent_id: str, agent_data: Dict[str, Any]) -> "AgentEvent":
        """Create agent updated event"""
        return cls(entity_id=agent_id, event_type="updated", data=agent_data)

    @classmethod
    def deleted(cls, agent_id: str) -> "AgentEvent":
        """Create agent deleted event"""
        return cls(entity_id=agent_id, event_type="deleted", data={})

    @classmethod
    def knowledge_created(cls, agent_id: str, knowledge_data: Dict[str, Any]) -> "AgentEvent":
        """Create agent knowledge created event"""
        return cls(entity_id=agent_id, event_type="knowledge_created", data=knowledge_data)
