"""
Agent Knowledge Factory
Creates shared knowledge base with agent-specific metadata filtering
"""

import logging

from app.events.agents.publisher import AgentEventPublisher


logger = logging.getLogger(__name__)


class AgentKnowledgeFactory:
    """Factory for creating shared knowledge base with agent filtering"""

    def __init__(self, db_url: str, event_publisher: AgentEventPublisher):
        self.db_url = db_url
        self.event_publisher = event_publisher

    async def create_knowledge_for_agent(
        self,
        agent_id: str,
        agent_name: str,
    ):
        """Create shared knowledge base with agent-specific metadata filtering"""
        return await self._create_shared_knowledge(agent_id, agent_name)

    async def _create_shared_knowledge(self, agent_id: str, agent_name: str):
        """Create shared knowledge base for agent"""
        from agno.db.postgres.postgres import PostgresDb
        from agno.knowledge.embedder.openai import OpenAIEmbedder
        from agno.knowledge.knowledge import Knowledge
        from agno.vectordb.pgvector import PgVector
        from app.events.agents.events import AgentEvent

        embedder = OpenAIEmbedder()
        db = PostgresDb(db_url=self.db_url, knowledge_table="knowledge_contents")

        knowledge = Knowledge(
            name=f"Knowledge for {agent_name}",
            description="Knowledge with Agent Filtering",
            contents_db=db,
            vector_db=PgVector(
                table_name="knowledge_chunks",
                db_url=self.db_url,
                embedder=embedder,
            ),
        )

        # TODO: Publish knowledge creation event when needed
        # await self.event_publisher.publish(
        #     channel="agent.knowledge.created",
        #     data={
        #         "agent_id": agent_id,
        #         "name": agent_name,
        #         "knowledge_name": knowledge.name,
        #         "knowledge_description": knowledge.description,
        #     }
        # )

        logger.info(f"Created shared knowledge for agent {agent_name}")
        return knowledge
