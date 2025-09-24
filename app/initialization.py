"""
Application initialization - handles database, agents, and AgentOS setup
Following CLAUDE.md: boring, direct, single responsibility
"""

import logging
from pathlib import Path

from agno.agent import Agent as AgnoAgent
from agno.os import AgentOS
from dotenv import load_dotenv
from infrastructure.database import Base
from infrastructure.database.session import EngineType, engines


logger = logging.getLogger(__name__)


class AgentLoader:
    """Loads and converts agents from database - shared by AgentOS and webhook processing"""

    def __init__(self, agent_repository, agno_agent_converter):
        self.agent_repository = agent_repository
        self.agno_agent_converter = agno_agent_converter
        # AgentOS agents (all active agents)
        self._loaded_agents = []
        self._agno_agents = []
        # Webhook agents (WhatsApp-enabled only)
        self._webhook_agno_agents = []

    async def load_all_active_agents(self):
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
            raise RuntimeError(msg)

        logger.info(f"Successfully loaded {len(self._agno_agents)} agents")
        return self._loaded_agents, self._agno_agents

    async def load_webhook_agents(self):
        """Load agents filtered for webhook processing"""
        logger.info("Loading webhook-enabled agents from database...")
        db_agents = await self.agent_repository.get_agents_by_status(status=True)
        logger.info(f"Found {len(db_agents)} active agents in database")

        webhook_agents = [
            agent for agent in db_agents if agent.whatsapp_enabled and agent.whatsapp_token
        ]
        logger.info(f"Filtered to {len(webhook_agents)} WhatsApp-enabled agents")

        self._webhook_agno_agents = await self.agno_agent_converter.convert_agents_for_webhook(
            webhook_agents
        )

        logger.info(f"Successfully loaded {len(self._webhook_agno_agents)} webhook agents")
        return webhook_agents, self._webhook_agno_agents

    def find_agno_agent_by_id(self, agent_id: str) -> AgnoAgent | None:
        """Find AgnoAgent by ID in webhook agents (for webhook processing)"""
        for agno_agent in self._webhook_agno_agents:
            if agno_agent.id == agent_id:
                return agno_agent
        return None

    @property
    def loaded_agents(self):
        """Get the loaded DB agents"""
        return self._loaded_agents.copy()

    @property
    def agno_agents(self):
        """Get the AgnoAgent instances"""
        return self._agno_agents.copy()

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


def setup_agent_os_with_app(agno_agents, fastapi_app):
    """Setup AgentOS with FastAPI app - direct and simple"""
    if not agno_agents:
        raise RuntimeError("No agents loaded for AgentOS setup")

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
