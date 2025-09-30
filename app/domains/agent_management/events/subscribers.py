"""Agent event subscribers"""

from app.shared.events.domain_registry import EventRegistry

from .events import AgentEventPayload
from .handlers import (
    handle_agent_created,
    handle_agent_deleted,
    handle_agent_knowledge_created,
    handle_agent_knowledge_deleted,
    handle_agent_updated,
)


# Agent domain event registry - declarative configuration
AGENT_EVENTS = EventRegistry(
    "agents",
    AgentEventPayload,
    {
        "created": handle_agent_created,
        "updated": handle_agent_updated,
        "deleted": handle_agent_deleted,
        "knowledge_created": handle_agent_knowledge_created,
        "knowledge_deleted": handle_agent_knowledge_deleted,
    },
)
