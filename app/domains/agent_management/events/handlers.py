"""Agent event handlers - Pure business logic"""

from core.logger import get_module_logger

from .events import AgentEventPayload


logger = get_module_logger(__name__)


async def handle_agent_created(data: AgentEventPayload) -> None:
    """Handle agent created events"""
    agent_id = data["entity_id"]
    agent_data = data["data"]
    agent_short = agent_id[:8]

    # Single compact log with all essential info
    if "name" in agent_data:
        logger.info(f"✅ HANDLER: Agent '{agent_data['name']}' [{agent_short}] - CREATED")
    else:
        logger.info(f"✅ HANDLER: Agent [{agent_short}] - CREATED")


async def handle_agent_updated(data: AgentEventPayload) -> None:
    """Handle agent updated events"""
    agent_id = data["entity_id"]
    agent_data = data["data"]
    agent_short = agent_id[:8]

    # Single compact log with all essential info
    if "name" in agent_data:
        logger.info(f"🔄 HANDLER: Agent '{agent_data['name']}' [{agent_short}] - UPDATED")
    else:
        logger.info(f"🔄 HANDLER: Agent [{agent_short}] - UPDATED")


async def handle_agent_deleted(data: AgentEventPayload) -> None:
    """Handle agent deleted events"""
    agent_id = data["entity_id"]
    agent_short = agent_id[:8]

    logger.info(f"❌ HANDLER: Agent [{agent_short}] - DELETED")


async def handle_agent_knowledge_created(data: AgentEventPayload) -> None:
    """Handle agent knowledge created events"""
    agent_id = data["entity_id"]
    agent_short = agent_id[:8]

    logger.info(f"📚 HANDLER: Agent [{agent_short}] - KNOWLEDGE CREATED")
