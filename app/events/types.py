"""
Unified event types aggregating all domain-specific events
"""

from enum import Enum

# Import all domain-specific event types
from app.agents.events.types import AgentEventType
from app.tools.events.types import ToolEventType
from app.knowledge.events.types import KnowledgeEventType


class EventType(str, Enum):
    """Unified event types aggregating all domain-specific events"""

    # Agent Events
    AGENT_CREATED = AgentEventType.AGENT_CREATED
    AGENT_UPDATED = AgentEventType.AGENT_UPDATED
    AGENT_DELETED = AgentEventType.AGENT_DELETED
    AGENT_ACTIVATED = AgentEventType.AGENT_ACTIVATED
    AGENT_DEACTIVATED = AgentEventType.AGENT_DEACTIVATED

    # Tool Events
    TOOL_REGISTERED = ToolEventType.TOOL_REGISTERED
    TOOL_UNREGISTERED = ToolEventType.TOOL_UNREGISTERED
    TOOL_EXECUTED = ToolEventType.TOOL_EXECUTED
    TOOL_FAILED = ToolEventType.TOOL_FAILED

    # Knowledge Events
    MEMORY_CREATED = KnowledgeEventType.MEMORY_CREATED
    MEMORY_UPDATED = KnowledgeEventType.MEMORY_UPDATED
    MEMORY_DELETED = KnowledgeEventType.MEMORY_DELETED
    MEMORY_ACCESSED = KnowledgeEventType.MEMORY_ACCESSED
    KNOWLEDGE_SEARCHED = KnowledgeEventType.KNOWLEDGE_SEARCHED

    # System Events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"

    # AgentOS Events
    AGENT_OS_LOAD_AGENTS = "agent_os.load_agents"
