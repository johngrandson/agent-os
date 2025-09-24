"""
Application initialization - handles database, agents, and AgentOS setup
Following CLAUDE.md: boring, direct, single responsibility
"""

import logging
from pathlib import Path

from agno.agent import Agent as AgnoAgent
from agno.os import AgentOS
from app.agents.agent import Agent
from dotenv import load_dotenv
from infrastructure.database import Base
from infrastructure.database.session import EngineType, engines

from fastapi import FastAPI


logger = logging.getLogger(__name__)


class AgentCache:
    """Simple agent cache for storage and lookup"""

    def __init__(self, agent_repository, agno_agent_converter):
        self.agent_repository = agent_repository
        self.agno_agent_converter = agno_agent_converter
        self._loaded_agents: list[Agent] = []
        self._agno_agents: list[AgnoAgent] = []

    async def load_all_agents(self):
        """Load all active agents from database"""
        logger.info("Loading all active agents from database...")
        db_agents = await self.agent_repository.get_agents_by_status(status=True)
        logger.info(f"Found {len(db_agents)} active agents in database")

        self._loaded_agents = db_agents
        self._agno_agents = await self.agno_agent_converter.convert_agents_for_agent_os(db_agents)

        if not self._agno_agents:
            msg = (
                "No active agents found in database. At least one active agent is required "
                "for the application."
            )
            logger.warning(msg)

        logger.info(f"Successfully loaded {len(self._agno_agents)} agents")
        return self._loaded_agents, self._agno_agents

    def find_agent_by_id(self, agent_id: str) -> AgnoAgent | None:
        """Find AgnoAgent by ID"""
        for agno_agent in self._agno_agents:
            if agno_agent.id == agent_id:
                return agno_agent
        return None

    def get_all_agents(self) -> list[AgnoAgent]:
        """Get all loaded AgnoAgent instances"""
        return self._agno_agents.copy()

    def get_loaded_db_agents(self) -> list[Agent]:
        """Get the loaded DB agents"""
        return self._loaded_agents.copy()

    def has_agents(self) -> bool:
        """Check if agents are loaded"""
        return len(self._agno_agents) > 0


async def initialize_database():
    """Initialize database tables - direct and simple"""
    _ensure_environment_loaded()

    try:
        async with engines[EngineType.WRITER].begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def setup_agent_os_with_app(agno_agents: list[AgnoAgent], fastapi_app: FastAPI) -> FastAPI:
    """Setup AgentOS with FastAPI app - direct and simple"""
    if not agno_agents:
        msg = "No agents loaded for AgentOS setup"
        logger.warning(msg)

    if len(agno_agents) == 0:
        agno_agents.append(
            AgnoAgent(
                id="default-agent",
                name="Default Agent",
                description="A default agent created because no agents were found.",
            )
        )

    logger.info(f"Setting up AgentOS with {len(agno_agents)} agents")
    agent_os = AgentOS(agents=agno_agents, fastapi_app=fastapi_app)
    final_app = agent_os.get_app()

    logger.info("AgentOS integration completed successfully")
    return final_app


def _ensure_environment_loaded():
    """Ensure environment variables are loaded with local override"""
    if Path(".env.local").exists():
        load_dotenv(".env.local", override=True)
    else:
        load_dotenv(override=True)
