"""Agent event handlers"""

import logging

from app.agents.api.schemas import AgentResponse, CreateAgentResponse
from app.events.core.registry import event_registry
from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)

# Create agent-specific router
agent_router = RedisRouter()


@agent_router.subscriber("agent.created")
async def handle_agent_created(data: CreateAgentResponse):
    """Handle agent created events"""
    logger.info(f"Agent created: {data.id}")
    logger.debug(f"Agent data: {data.model_dump()}")


@agent_router.subscriber("agent.updated")
async def handle_agent_updated(data: AgentResponse):
    """Handle agent updated events"""
    logger.info(f"Agent updated: {data.id}")
    logger.debug(f"Updated data: {data.model_dump()}")


@agent_router.subscriber("agent.deleted")
async def handle_agent_deleted(data: dict):
    """Handle agent deleted events"""
    entity_id = data.get("entity_id")

    logger.info(f"Agent deleted: {entity_id}")


@agent_router.subscriber("agent.knowledge_created")
async def handle_agent_knowledge_created(data: dict):
    """Handle agent knowledge created events"""
    entity_id = data.get("entity_id")
    knowledge_data = data.get("data", {})

    logger.info(f"Knowledge created for agent: {entity_id}")
    logger.debug(f"Knowledge data: {knowledge_data}")


# Register the router with the event registry
event_registry.register_domain_router("agent", agent_router)
