"""Agent conversion logic from database agents to AgnoAgent instances"""

import logging

from agno.agent import Agent as AgnoAgent
from app.agents.agent import Agent
from app.providers.agno.database_factory import AgnoDatabaseFactory
from app.providers.agno.knowledge_adapter import AgnoKnowledgeAdapter
from app.providers.agno.model_factory import AgnoModelFactory


logger = logging.getLogger(__name__)


class AgnoAgentConverter:
    """Converts database Agent instances to AgnoAgent instances"""

    def __init__(
        self,
        knowledge_adapter: AgnoKnowledgeAdapter,
        model_factory: AgnoModelFactory,
    ):
        self.knowledge_adapter = knowledge_adapter
        self.model_factory = model_factory
        # Create database for agent history storage
        self.db = AgnoDatabaseFactory.create_postgres_db()

    async def convert_agent(
        self,
        db_agent: Agent,
        search_knowledge: bool = True,
        add_history_to_context: bool = True,
        num_history_runs: int = 3,
        add_datetime_to_context: bool = True,
        markdown: bool = False,
    ) -> AgnoAgent:
        """
        Convert a database agent to an AgnoAgent instance.

        Args:
            db_agent: Database agent instance
            search_knowledge: Enable knowledge search
            add_history_to_context: Include conversation history
            num_history_runs: Number of history runs to include
            add_datetime_to_context: Add datetime to context
            markdown: Enable markdown formatting

        Returns:
            Configured AgnoAgent instance
        """
        logger.info(f"Converting agent {db_agent.name} to AgnoAgent")

        # Create knowledge for the agent
        knowledge = await self.knowledge_adapter.create_knowledge_for_agent(
            agent_id=str(db_agent.id),
            agent_name=db_agent.name,
        )

        # Configure knowledge filters
        agent_knowledge_filters = {
            "agent_id": str(db_agent.id),
        }

        # Get appropriate model based on agent's llm_model preference
        if db_agent.llm_model:
            model = self.model_factory.create_openai_model(db_agent.llm_model)
        else:
            model = self.model_factory.create_default_model()

        # Build instructions with language context
        instructions = db_agent.instructions or []
        if db_agent.default_language:
            language_instruction = (
                f"Always respond in the default language: {db_agent.default_language}"
            )
            instructions = [language_instruction] + instructions

        # Adjust history settings based on database availability
        if self.db is None:
            # No database available - disable history to avoid warning
            add_history_to_context = False
            logger.warning(
                f"Database not available for agent {db_agent.name}. "
                "Conversation history will not be stored or used in context."
            )

        # Create AgnoAgent with configuration
        agno_agent = AgnoAgent(
            id=str(db_agent.id),
            name=db_agent.name,
            knowledge=knowledge,
            search_knowledge=search_knowledge,
            add_history_to_context=add_history_to_context,
            num_history_runs=num_history_runs,
            add_datetime_to_context=add_datetime_to_context,
            enable_user_memories=True,
            enable_agentic_memory=True,
            markdown=markdown,
            instructions=instructions,
            knowledge_filters=agent_knowledge_filters,
            model=model,
            db=self.db,  # Add database for history storage
        )

        logger.info(f"Successfully converted agent {db_agent.name}")
        return agno_agent

    async def convert_agents_for_webhook(self, db_agents: list[Agent]) -> list[AgnoAgent]:
        """Convert multiple agents for webhook processing with webhook-specific config"""
        logger.info(f"Converting {len(db_agents)} agents for webhook processing")

        agno_agents = []
        for db_agent in db_agents:
            try:
                agno_agent = await self.convert_agent(
                    db_agent,
                    markdown=True,
                    search_knowledge=True,
                    add_history_to_context=True,
                    num_history_runs=3,
                    add_datetime_to_context=True,
                )
                agno_agents.append(agno_agent)
            except Exception as e:
                logger.error(f"Failed to convert webhook agent {db_agent.name}: {e}")
                # Continue processing other agents
                continue

        logger.info(f"Successfully converted {len(agno_agents)} webhook agents")
        return agno_agents

    async def convert_agents_for_agent_os(self, db_agents: list[Agent]) -> list[AgnoAgent]:
        """Convert multiple agents for AgentOS with AgentOS-specific config"""
        logger.info(f"Converting {len(db_agents)} agents for AgentOS")

        agno_agents = []
        for db_agent in db_agents:
            try:
                agno_agent = await self.convert_agent(
                    db_agent,
                    search_knowledge=True,
                    add_history_to_context=True,
                    num_history_runs=3,
                    add_datetime_to_context=True,
                )
                agno_agents.append(agno_agent)
            except Exception as e:
                logger.error(f"Failed to convert AgentOS agent {db_agent.name}: {e}")
                # Continue processing other agents
                continue

        logger.info(f"Successfully converted {len(agno_agents)} AgentOS agents")
        return agno_agents
