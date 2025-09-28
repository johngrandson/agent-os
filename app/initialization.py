"""
Application initialization - handles database, agents, and AgentOS setup
Following CLAUDE.md: boring, direct, single responsibility
"""

from pathlib import Path
from typing import Any

from app.domains.agent_management.agent import Agent
from app.infrastructure.providers.base import AgentProvider, RuntimeAgent
from core.logger import get_module_logger
from dotenv import load_dotenv
from infrastructure.database import Base
from infrastructure.database.session import EngineType, engines


logger = get_module_logger(__name__)


class AgentCache:
    """Simple agent cache for storage and lookup"""

    def __init__(self, agent_repository: Any, agent_provider: AgentProvider) -> None:
        self.agent_repository = agent_repository
        self.agent_provider = agent_provider
        self._loaded_agents: list[Agent] = []
        self._runtime_agents: list[RuntimeAgent] = []

    async def load_all_agents(self) -> tuple[list[Agent], list[RuntimeAgent]]:
        """Load all active agents from database"""
        logger.info("Loading all active agents from database...")
        db_agents = await self.agent_repository.get_agents_by_status(status=True)
        logger.info(f"Found {len(db_agents)} active agents in database")

        self._loaded_agents = db_agents
        self._runtime_agents = await self.agent_provider.convert_agents_for_runtime(db_agents)

        if not self._runtime_agents:
            msg = (
                "No active agents found in database. At least one active agent is required "
                "for the application."
            )
            logger.warning(msg)

        logger.info(f"Successfully loaded {len(self._runtime_agents)} agents")
        return self._loaded_agents, self._runtime_agents

    def find_agent_by_id(self, agent_id: str) -> RuntimeAgent | None:
        """Find runtime agent by ID"""
        for runtime_agent in self._runtime_agents:
            if runtime_agent.id == agent_id:
                return runtime_agent
        return None

    def get_all_agents(self) -> list[RuntimeAgent]:
        """Get all loaded runtime agent instances"""
        return self._runtime_agents.copy()

    def get_loaded_db_agents(self) -> list[Agent]:
        """Get the loaded DB agents"""
        return self._loaded_agents.copy()

    def has_agents(self) -> bool:
        """Check if agents are loaded"""
        return len(self._runtime_agents) > 0


async def initialize_database() -> None:
    """Initialize database tables - direct and simple"""
    _ensure_environment_loaded()

    try:
        async with engines[EngineType.WRITER].begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def _ensure_environment_loaded() -> None:
    """Ensure environment variables are loaded with local override"""
    if Path(".env.local").exists():
        load_dotenv(".env.local", override=True)
    else:
        load_dotenv(override=True)
