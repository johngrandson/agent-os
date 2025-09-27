"""Agent event handlers"""

from app.events.core.registry import event_registry
from core.logger import get_module_logger
from faststream.redis import RedisRouter

from .events import AgentEventPayload


logger = get_module_logger(__name__)

# Create agent-specific router
agent_router = RedisRouter()


@agent_router.subscriber("agent.created")
async def handle_agent_created(data: AgentEventPayload):
    """Handle agent created events"""
    agent_id = data["entity_id"]
    agent_data = data["data"]
    agent_short = agent_id[:8]

    # Single compact log with all essential info
    if "name" in agent_data:
        logger.info(f"✅ HANDLER: Agent '{agent_data['name']}' [{agent_short}] - CREATED")
    else:
        logger.info(f"✅ HANDLER: Agent [{agent_short}] - CREATED")


@agent_router.subscriber("agent.updated")
async def handle_agent_updated(data: AgentEventPayload):
    """Handle agent updated events"""
    agent_id = data["entity_id"]
    agent_data = data["data"]
    agent_short = agent_id[:8]

    # Single compact log with all essential info
    if "name" in agent_data:
        logger.info(f"🔄 HANDLER: Agent '{agent_data['name']}' [{agent_short}] - UPDATED")
    else:
        logger.info(f"🔄 HANDLER: Agent [{agent_short}] - UPDATED")


@agent_router.subscriber("agent.deleted")
async def handle_agent_deleted(data: AgentEventPayload):
    """Handle agent deleted events"""
    agent_id = data["entity_id"]
    agent_short = agent_id[:8]

    logger.info(f"❌ HANDLER: Agent [{agent_short}] - DELETED")


@agent_router.subscriber("agent.knowledge_created")
async def handle_agent_knowledge_created(data: AgentEventPayload):
    """Handle agent knowledge created events"""
    agent_id = data["entity_id"]
    agent_short = agent_id[:8]

    logger.info(f"📚 HANDLER: Agent [{agent_short}] - KNOWLEDGE CREATED")


# Register the router with the event registry
event_registry.register_domain_router("agent", agent_router)
