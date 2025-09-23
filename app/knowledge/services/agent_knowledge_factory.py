"""
Agent Knowledge Factory
Creates shared knowledge base with agent-specific metadata filtering
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AgentKnowledgeFactory:
    """Factory for creating shared knowledge base with agent filtering"""

    def __init__(self, db_url: str):
        self.db_url = db_url

    async def create_knowledge_for_agent(
        self,
        agent_id: str,
        agent_name: str,
        knowledge_config: Optional[Dict[str, Any]] = None,
    ):
        """Create shared knowledge base with agent-specific metadata filtering"""
        return self._create_shared_knowledge(agent_id, agent_name)

    def _create_shared_knowledge(self, agent_id: str, agent_name: str):
        """Create shared knowledge base for agent"""
        from agno.vectordb.pgvector import PgVector
        from agno.knowledge.embedder.openai import OpenAIEmbedder
        from agno.db.postgres.postgres import PostgresDb
        from agno.knowledge.knowledge import Knowledge

        embedder = OpenAIEmbedder()
        db = PostgresDb(db_url=self.db_url, knowledge_table="knowledge_contents")

        knowledge = Knowledge(
            name=f"Knowledge for {agent_name}",
            description="Shared Knowledge with Agent Filtering",
            contents_db=db,
            vector_db=PgVector(
                table_name="knowledge_chunks",
                db_url=self.db_url,
                embedder=embedder,
            ),
        )

        logger.info(f"Created shared knowledge for agent {agent_name}")
        return knowledge
