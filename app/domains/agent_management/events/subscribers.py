"""Agent event subscribers"""

from app.shared.events.registry import event_registry
from faststream.redis import RedisRouter

from .events import AgentEventPayload
from .handlers import (
    handle_agent_created,
    handle_agent_deleted,
    handle_agent_knowledge_created,
    handle_agent_updated,
)


# Create agent-specific router
agent_router = RedisRouter()


@agent_router.subscriber("agents.created")
async def agent_created_subscriber(data: AgentEventPayload) -> None:
    """Agent created event subscriber"""
    await handle_agent_created(data)


@agent_router.subscriber("agents.updated")
async def agent_updated_subscriber(data: AgentEventPayload) -> None:
    """Agent updated event subscriber"""
    await handle_agent_updated(data)


@agent_router.subscriber("agents.deleted")
async def agent_deleted_subscriber(data: AgentEventPayload) -> None:
    """Agent deleted event subscriber"""
    await handle_agent_deleted(data)


@agent_router.subscriber("agents.knowledge_created")
async def agent_knowledge_created_subscriber(data: AgentEventPayload) -> None:
    """Agent knowledge created event subscriber"""
    await handle_agent_knowledge_created(data)


# Register the router with the event registry
event_registry.register_domain_router("agents", agent_router)
