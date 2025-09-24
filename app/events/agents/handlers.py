"""Agent event handlers"""

import logging
from typing import Any, Dict

from app.events.core.registry import event_registry
from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)

# Create agent-specific router
agent_router = RedisRouter()


@agent_router.subscriber("agent.created")
async def handle_agent_created(data: Dict[str, Any]):
    """Handle agent created events"""
    entity_id = data.get("entity_id")
    event_data = data.get("data", {})

    logger.info(f"Agent created: {entity_id}")
    logger.debug(f"Agent data: {event_data}")

    # Add any agent creation side effects here
    # e.g., send notifications, update caches, trigger workflows


@agent_router.subscriber("agent.updated")
async def handle_agent_updated(data: Dict[str, Any]):
    """Handle agent updated events"""
    entity_id = data.get("entity_id")
    event_data = data.get("data", {})

    logger.info(f"Agent updated: {entity_id}")
    logger.debug(f"Updated data: {event_data}")

    # Add any agent update side effects here
    # e.g., invalidate caches, update search index


@agent_router.subscriber("agent.deleted")
async def handle_agent_deleted(data: Dict[str, Any]):
    """Handle agent deleted events"""
    entity_id = data.get("entity_id")

    logger.info(f"Agent deleted: {entity_id}")

    # Add any agent deletion side effects here
    # e.g., cleanup resources, update related entities


@agent_router.subscriber("agent.knowledge_created")
async def handle_agent_knowledge_created(data: Dict[str, Any]):
    """Handle agent knowledge created events"""
    entity_id = data.get("entity_id")
    knowledge_data = data.get("data", {})

    logger.info(f"Knowledge created for agent: {entity_id}")
    logger.debug(f"Knowledge data: {knowledge_data}")

    # Add any knowledge creation side effects here


# Register the router with the event registry
event_registry.register_domain_router("agent", agent_router)
