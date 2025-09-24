"""Knowledge system adapter for Agno integration"""

import logging
from typing import Any

from app.events.agents.publisher import AgentEventPublisher
from app.knowledge.services.agent_knowledge_factory import AgentKnowledgeFactory


logger = logging.getLogger(__name__)


class AgnoKnowledgeAdapter:
    """Adapter for integrating Agno with the knowledge system"""

    def __init__(self, db_url: str, event_publisher: AgentEventPublisher):
        self.knowledge_factory = AgentKnowledgeFactory(db_url, event_publisher)
        logger.info("AgnoKnowledgeAdapter initialized")

    async def create_knowledge_for_agent(self, agent_id: str, agent_name: str) -> Any:
        """
        Create knowledge instance for an agent.

        Args:
            agent_id: Agent UUID as string
            agent_name: Agent name for logging

        Returns:
            Knowledge instance for the agent
        """
        logger.info(f"Creating knowledge for agent {agent_name} (ID: {agent_id})")

        try:
            knowledge = await self.knowledge_factory.create_knowledge_for_agent(
                agent_id=agent_id,
                agent_name=agent_name,
            )
            logger.info(f"Successfully created knowledge for agent {agent_name}")
            return knowledge

        except Exception as e:
            logger.error(f"Failed to create knowledge for agent {agent_name}: {e}")
            raise
