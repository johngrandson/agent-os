"""
Agent event types
"""

from enum import Enum


class AgentEventType(str, Enum):
    """Types of agent-related events"""

    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_ACTIVATED = "agent.activated"
    AGENT_DEACTIVATED = "agent.deactivated"
