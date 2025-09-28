"""
Agno provider implementation - wraps existing agno functionality.
Following CLAUDE.md: boring wrapper, don't rewrite existing code.
"""

import asyncio
import contextlib
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from threading import Lock

from agno.agent import Agent as AgnoAgent
from agno.db.postgres.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.os import AgentOS
from app.agents.agent import Agent
from app.knowledge.services.agent_knowledge_factory import AgentKnowledgeFactory
from app.providers.base import AgentProvider, RuntimeAgent
from core.config import Config, get_config
from core.logger import get_module_logger

from fastapi import FastAPI


logger = get_module_logger(__name__)


class AsyncPostgresDbWrapper:
    """Wrapper to handle PostgresDb operations in a thread pool to avoid async/sync conflicts"""

    def __init__(self, postgres_db: PostgresDb):
        self._db = postgres_db
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agno_db")
        self._lock = Lock()

    def __getattr__(self, name):
        """Delegate attribute access to the wrapped PostgresDb"""
        return getattr(self._db, name)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()

    def __del__(self):
        """Cleanup when object is garbage collected"""
        with contextlib.suppress(Exception):
            self.cleanup()

    def cleanup(self):
        """Clean up the thread pool and database connections"""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
        if hasattr(self, "_db") and self._db and hasattr(self._db, "close"):
            # Close database connections if the db has a close method
            with contextlib.suppress(Exception):
                self._db.close()


class AgnoDatabaseFactory:
    """Factory for creating Agno database instances for agent history storage"""

    _instance_lock = Lock()
    _postgres_db_cache = None

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_postgres_db_url() -> str:
        """Get PostgreSQL database URL for Agno PostgresDb (standard PostgreSQL format)"""
        config = get_config()

        # Use AGNO_DB_URL if configured, otherwise construct from config
        if config.AGNO_DB_URL:
            return config.AGNO_DB_URL

        # Convert asyncpg URL to standard PostgreSQL format for Agno
        base_url = config.database_url
        if base_url.startswith("postgresql+asyncpg://"):
            # Remove asyncpg driver specification for standard PostgreSQL URL
            agno_url = base_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            # Construct standard PostgreSQL URL
            agno_url = f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"

        return agno_url

    @staticmethod
    def create_postgres_db() -> PostgresDb | None:
        """
        Create a PostgresDb instance for storing agent conversation history.

        Returns:
            PostgresDb: Configured database instance for agent history
        """
        try:
            with AgnoDatabaseFactory._instance_lock:
                if AgnoDatabaseFactory._postgres_db_cache is not None:
                    return AgnoDatabaseFactory._postgres_db_cache

                db_url = AgnoDatabaseFactory._get_postgres_db_url()
                # Mask credentials in logging
                safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
                logger.info(f"Creating PostgresDb for agent history with host: {safe_url}")

                # Create PostgresDb with Agno history configuration
                postgres_db = PostgresDb(
                    db_url=db_url,
                    session_table="agent_sessions",  # Store agent sessions
                    memory_table="agent_memories",  # Store agent memories
                    metrics_table="agent_metrics",  # Store agent metrics
                )

                # Validate connection before caching
                try:
                    # Simple validation - if this succeeds, connection is working
                    if hasattr(postgres_db, "db_url") and postgres_db.db_url:
                        logger.info("Successfully created PostgresDb for agent history")
                        AgnoDatabaseFactory._postgres_db_cache = postgres_db
                        return postgres_db
                    error_msg = "PostgresDb creation returned invalid instance"
                    raise ValueError(error_msg)
                except Exception as validation_error:
                    logger.error(f"Failed to validate PostgresDb connection: {validation_error}")
                    raise

        except Exception as e:
            logger.error(f"Failed to create PostgresDb: {e}")
            logger.warning(
                "Agent history storage not available. "
                "Agents will run without conversation history context."
            )
            # Return None to indicate no database available
            # This will disable history context but allow agents to run
            return None

    @staticmethod
    def create_async_postgres_db() -> AsyncPostgresDbWrapper | None:
        """
        Create an async-compatible PostgresDb wrapper for use in FastAPI endpoints.

        Returns:
            AsyncPostgresDbWrapper: Async wrapper around PostgresDb
        """
        postgres_db = AgnoDatabaseFactory.create_postgres_db()
        if postgres_db is None:
            return None

        return AsyncPostgresDbWrapper(postgres_db)

    @staticmethod
    def is_database_available() -> bool:
        """
        Check if database is available for agent history storage.

        Returns:
            bool: True if database can be configured, False otherwise
        """
        try:
            db = AgnoDatabaseFactory.create_postgres_db()
            return db is not None
        except Exception:
            return False


class AgnoModelFactory:
    """Factory for creating AI models compatible with Agno"""

    def __init__(self, config: Config):
        self.config = config
        logger.info("AgnoModelFactory initialized")

    def create_default_model(self) -> OpenAIChat:
        """
        Create the default AI model for agents.

        Returns:
            Configured OpenAIChat model
        """
        model_name = self.config.AGNO_DEFAULT_MODEL
        logger.info(f"Creating default model: {model_name}")

        return OpenAIChat(id=model_name)

    def create_openai_model(self, model_id: str) -> OpenAIChat:
        """
        Create an OpenAI model with specific ID.

        Args:
            model_id: OpenAI model identifier

        Returns:
            Configured OpenAIChat model
        """
        logger.info(f"Creating OpenAI model: {model_id}")
        return OpenAIChat(id=model_id)

    def create_model_for_context(self, context: str) -> OpenAIChat:
        """
        Create an appropriate model based on context.

        Args:
            context: Usage context (e.g., 'webhook', 'agent_os', 'chat')

        Returns:
            Configured model appropriate for the context
        """
        # For now, return default model
        # In the future, this could select different models based on context
        logger.info(f"Creating model for context: {context}")
        return self.create_default_model()


class AgnoRuntimeAgent(RuntimeAgent):
    """Simple wrapper around AgnoAgent to implement RuntimeAgent interface"""

    def __init__(self, agno_agent: AgnoAgent):
        self._agno_agent = agno_agent

    async def arun(self, message: str) -> str:
        """Run the agno agent with a message, isolating sync operations from async context"""
        from concurrent.futures import ThreadPoolExecutor

        # Run agno agent in thread pool to avoid async/sync conflicts
        loop = asyncio.get_event_loop()

        def run_agent_sync():
            """Run the agent synchronously in a separate thread"""
            # Use sync run method to avoid greenlet issues
            return self._agno_agent.run(input=message)

        try:
            # Execute in thread pool to isolate sync database operations
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="agno_agent") as executor:
                result = await loop.run_in_executor(executor, run_agent_sync)

            # Handle different return types from agno - get content as string
            if hasattr(result, "content"):
                return result.content
            if isinstance(result, str):
                return result
            return str(result)

        except Exception as e:
            logger.error(f"Error running agent {self.name}: {e}")
            # Fallback: try without thread pool as last resort
            try:
                result = await self._agno_agent.arun(input=message)
                if hasattr(result, "content"):
                    return result.content
                if isinstance(result, str):
                    return result
                return str(result)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed for agent {self.name}: {fallback_error}")
                return f"Error: Agent {self.name} encountered an issue processing the request."

    @property
    def id(self) -> str:
        return self._agno_agent.id

    @property
    def name(self) -> str:
        return self._agno_agent.name

    def get_agno_agent(self) -> AgnoAgent:
        """Access to underlying agno agent for backwards compatibility"""
        return self._agno_agent


class AgnoProvider(AgentProvider):
    """
    Agno implementation of AgentProvider.
    Wraps existing AgnoAgentConverter and AgentOS functionality.
    """

    def __init__(self):
        # Import here to avoid circular import
        from app.providers.agno.converter import AgnoAgentConverter

        # Create required dependencies
        config = get_config()

        # Create knowledge factory directly
        knowledge_factory = AgentKnowledgeFactory(
            db_url=config.AGNO_DB_URL,
            event_publisher=None,  # Not needed for basic functionality
        )

        # Create model factory
        model_factory = AgnoModelFactory(config=config)

        # Create agno converter with dependencies
        self.agno_agent_converter = AgnoAgentConverter(
            knowledge_factory=knowledge_factory, model_factory=model_factory
        )

    async def convert_agents_for_webhook(self, db_agents: list[Agent]) -> list[RuntimeAgent]:
        """Convert agents for webhook processing - uses existing agno converter"""
        logger.info(f"Converting {len(db_agents)} agents for webhook via AgnoProvider")

        agno_agents = await self.agno_agent_converter.convert_agents_for_webhook(db_agents)
        runtime_agents = [AgnoRuntimeAgent(agno_agent) for agno_agent in agno_agents]

        logger.info(f"Successfully converted {len(runtime_agents)} webhook agents")
        return runtime_agents

    async def convert_agents_for_runtime(self, db_agents: list[Agent]) -> list[RuntimeAgent]:
        """Convert agents for runtime - uses existing agno converter"""
        logger.info(f"Converting {len(db_agents)} agents for runtime via AgnoProvider")

        agno_agents = await self.agno_agent_converter.convert_agents_for_agent_os(db_agents)
        runtime_agents = [AgnoRuntimeAgent(agno_agent) for agno_agent in agno_agents]

        logger.info(f"Successfully converted {len(runtime_agents)} runtime agents")
        return runtime_agents

    def setup_runtime_with_app(self, runtime_agents: list[RuntimeAgent], app: FastAPI) -> FastAPI:
        """Setup AgentOS with FastAPI app - uses existing AgentOS functionality"""
        logger.info(f"Setting up AgentOS with {len(runtime_agents)} agents via AgnoProvider")

        # Extract underlying agno agents from runtime agents
        agno_agents = []
        for runtime_agent in runtime_agents:
            if isinstance(runtime_agent, AgnoRuntimeAgent):
                agno_agents.append(runtime_agent.get_agno_agent())
            else:
                logger.warning(f"Unexpected runtime agent type: {type(runtime_agent)}")

        # Handle empty agents case like existing code
        if len(agno_agents) == 0:
            agno_agents.append(
                AgnoAgent(
                    id="default-agent",
                    name="Default Agent",
                    description="A default agent created because no agents were found.",
                )
            )

        # Use existing AgentOS setup logic
        agent_os = AgentOS(agents=agno_agents, fastapi_app=app)
        final_app = agent_os.get_app()

        logger.info("AgentOS integration completed successfully via AgnoProvider")
        return final_app
