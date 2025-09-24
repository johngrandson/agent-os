"""Agent domain events"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentEvent:
    """Base agent event class"""

    agent_id: str
    event_type: str
    data: Dict[str, Any]

    @classmethod
    def agent_created(cls, agent_id: str, agent_data: Dict[str, Any]) -> "AgentEvent":
        """Create an agent created event"""
        return cls(agent_id=agent_id, event_type="agent.created", data=agent_data)

    @classmethod
    def agent_updated(cls, agent_id: str, agent_data: Dict[str, Any]) -> "AgentEvent":
        """Create an agent updated event"""
        return cls(agent_id=agent_id, event_type="agent.updated", data=agent_data)

    @classmethod
    def agent_deleted(cls, agent_id: str) -> "AgentEvent":
        """Create an agent deleted event"""
        return cls(agent_id=agent_id, event_type="agent.deleted", data={})
