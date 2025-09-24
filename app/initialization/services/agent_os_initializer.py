"""
AgentOS integration service - loads agents from database and integrates with AgentOS
"""

import logging

from agno.agent import Agent as AgnoAgent
from agno.os import AgentOS
from app.agents.agent import Agent
from app.agents.repositories.agent_repository import AgentRepository
from app.events.agents.publisher import AgentEventPublisher
from app.integrations.agno import AgnoAgentConverter


logger = logging.getLogger(__name__)


class AgentOSInitializer:
    """Loads agents from database and integrates with AgentOS"""

    def __init__(
        self,
        agent_repository: AgentRepository,
        event_publisher: AgentEventPublisher,
        agno_agent_converter: AgnoAgentConverter,
    ):
        self.agent_repository = agent_repository
        self.event_publisher = event_publisher
        self.agno_agent_converter = agno_agent_converter

        # Agent storage
        self.loaded_agents: list[Agent] = []
        self.agno_agents: list[AgnoAgent] = []

    async def load_agents_from_database(self):
        """Load agents from database and convert to AgentOS format"""
        logger.info("Loading agents from database...")

        # Get agents from database
        db_agents = await self.agent_repository.get_agents_by_status(status=True)
        logger.info(f"Found {len(db_agents)} active agents in database")

        # Convert to AgnoAgent instances using integration layer
        self.agno_agents = await self.agno_agent_converter.convert_agents_for_agent_os(db_agents)
        self.loaded_agents = db_agents

        # Require at least one agent for AgentOS
        if not self.has_agents():
            msg = (
                "No active agents found in database. At least one active agent is required "
                "for the application."
            )
            raise RuntimeError(msg)

        logger.info(
            f"Successfully loaded {len(self.agno_agents)} agents and converted to AgentOS format"
        )

    def find_agno_agent_by_id(self, agent_id: str) -> AgnoAgent | None:
        """Find AgnoAgent by ID"""
        for agno_agent in self.agno_agents:
            if agno_agent.id == agent_id:
                return agno_agent
        return None

    async def load_agents_for_event_system(self):
        """Load agents for the event system initialization"""
        await self.load_agents_from_database()

    def get_loaded_agents(self) -> list[Agent]:
        """Get the loaded DB agents"""
        return self.loaded_agents.copy()

    def get_agno_agents(self) -> list[AgnoAgent]:
        """Get the AgnoAgent instances"""
        return self.agno_agents.copy()

    def has_agents(self) -> bool:
        """Check if agents are loaded"""
        return len(self.agno_agents) > 0

    def setup_with_app(self, fastapi_app):
        """Setup AgentOS with FastAPI app"""
        if not self.has_agents():
            msg = "No agents loaded. Load agents first before setting up AgentOS."
            raise RuntimeError(msg)

        logger.info(f"Setting up AgentOS with {len(self.agno_agents)} agents")

        # Create AgentOS instance
        agent_os = AgentOS(
            agents=self.get_agno_agents(),
            fastapi_app=fastapi_app,
        )
        final_app = agent_os.get_app()

        logger.info("AgentOS integration completed successfully")
        return final_app
