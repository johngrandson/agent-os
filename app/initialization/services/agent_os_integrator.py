"""
AgentOS integration service - loads agents from database and integrates with AgentOS
"""

import logging
import os
from dotenv import load_dotenv
from app.agents.repositories.agent_repository import AgentRepository
from app.knowledge.services.agent_knowledge_factory import AgentKnowledgeFactory
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS

logger = logging.getLogger(__name__)

load_dotenv()


class AgentOSIntegrator:
    """Loads agents from database and integrates with AgentOS"""

    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository
        self.loaded_agents = []
        self.agno_agents = []

        # Initialize knowledge factory
        db_url = os.getenv("AGNO_DB_URL", "")
        self.knowledge_factory = AgentKnowledgeFactory(db_url)

    async def load_agents_from_database(self):
        """Load agents from database and convert to AgentOS format"""
        logger.info("Loading agents from database...")

        # Get active agents from database
        db_agents = await self.agent_repository.get_agents_by_status(
            status=True, limit=50
        )

        logger.info(f"Found {len(db_agents)} active agents in database")

        # Store the DB agents
        self.loaded_agents = db_agents

        # Convert to AgentOS agents with isolated knowledge
        self.agno_agents = []
        for db_agent in db_agents:
            # Create agent-specific knowledge base
            knowledge = await self.knowledge_factory.create_knowledge_for_agent(
                agent_id=str(db_agent.id),
                agent_name=db_agent.name,
                knowledge_config=db_agent.knowledge_config,
            )

            # Configure strict agent-level knowledge filters
            agent_knowledge_filters = {
                "agent_id": str(db_agent.id),
            }

            agno_agent = AgnoAgent(
                id=str(db_agent.id),
                name=db_agent.name,
                knowledge=knowledge,
                search_knowledge=True,  # Enable knowledge search with filters
                knowledge_filters=agent_knowledge_filters,  # Apply strict agent isolation
                enable_agentic_knowledge_filters=False,  # Use manual filters only
                model=OpenAIChat(id=os.getenv("AGNO_DEFAULT_MODEL", "gpt-4o-mini")),
            )
            self.agno_agents.append(agno_agent)

            logger.info(f"Created agent {db_agent.name} with isolated knowledge")

        # Require at least one agent
        if not self.loaded_agents:
            raise RuntimeError(
                "No active agents found in database. At least one active agent is required for the application."
            )

        logger.info(
            f"Successfully loaded {len(self.loaded_agents)} agents and converted to AgentOS format"
        )

    async def load_agents_for_event_system(self):
        """Load agents for the event system initialization"""
        await self.load_agents_from_database()

    def get_loaded_agents(self):
        """Get the loaded DB agents"""
        return self.loaded_agents

    def get_agno_agents(self):
        """Get the AgentOS agents"""
        return self.agno_agents

    def has_agents(self):
        """Check if agents are loaded"""
        return len(self.loaded_agents) > 0

    def setup_with_app(self, fastapi_app):
        """Setup AgentOS with FastAPI app"""
        if not self.agno_agents:
            raise RuntimeError(
                "No agents loaded. Load agents first before setting up AgentOS."
            )

        logger.info(f"Setting up AgentOS with {len(self.agno_agents)} agents")

        # Create AgentOS instance
        agent_os = AgentOS(agents=self.agno_agents, fastapi_app=fastapi_app)
        final_app = agent_os.get_app()

        logger.info("AgentOS integration completed successfully")
        return final_app
