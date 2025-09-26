"""Knowledge system adapter for Agno integration"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.events.agents.publisher import AgentEventPublisher
from app.knowledge.services.agent_knowledge_factory import AgentKnowledgeFactory


logger = logging.getLogger(__name__)


class AgnoKnowledgeAdapter:
    """Adapter for integrating Agno with the knowledge system"""

    def __init__(self, db_url: str, event_publisher: AgentEventPublisher):
        self.knowledge_factory = AgentKnowledgeFactory(db_url, event_publisher)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agno_knowledge")
        logger.info("AgnoKnowledgeAdapter initialized")

    def _sync_create_knowledge(self, agent_id: str, agent_name: str) -> Any:
        """Synchronous knowledge creation to run in thread pool"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.knowledge_factory.create_knowledge_for_agent(
                    agent_id=agent_id,
                    agent_name=agent_name,
                )
            )
        finally:
            loop.close()

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
            # Run knowledge creation in thread pool to avoid async/sync conflicts
            loop = asyncio.get_event_loop()
            knowledge = await loop.run_in_executor(
                self._executor, self._sync_create_knowledge, agent_id, agent_name
            )
            logger.info(f"Successfully created knowledge for agent {agent_name}")
            return knowledge

        except Exception as e:
            logger.error(f"Failed to create knowledge for agent {agent_name}: {e}")
            # Return None instead of raising to allow agent to work without knowledge
            logger.warning(f"Agent {agent_name} will run without knowledge integration")
            return None

    def cleanup(self):
        """Clean up the thread pool"""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
