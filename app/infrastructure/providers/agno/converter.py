"""Agent conversion logic from database agents to AgnoAgent instances"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from agno.agent import Agent as AgnoAgent
from agno.tools.knowledge import KnowledgeTools
from app.domains.agent_management.agent import Agent
from app.domains.knowledge_base.services.agent_knowledge_factory import AgentKnowledgeFactory
from app.infrastructure.providers.agno.provider import AgnoDatabaseFactory, AgnoModelFactory
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class AgnoAgentConverter:
    """Converts database Agent instances to AgnoAgent instances"""

    def __init__(
        self,
        knowledge_factory: AgentKnowledgeFactory,
        model_factory: AgnoModelFactory,
    ):
        self.knowledge_factory = knowledge_factory
        self.model_factory = model_factory
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agno_knowledge")
        # Create database for agent history storage
        self.db = AgnoDatabaseFactory.create_postgres_db()

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

    def cleanup(self) -> None:
        """Clean up the thread pool"""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)

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
        knowledge = await self.create_knowledge_for_agent(
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
        instructions: list[str] = db_agent.instructions or []

        if db_agent.default_language:
            default_instructions: list[str] = [
                f"Always respond in the default language: {db_agent.default_language}",
                # Core search behavior
                (
                    "CRITICAL: Always search your knowledge base for domain-specific questions, "
                    "technical queries, or requests about locations, units, facilities, "
                    "procedures, or company-specific information."
                ),
                # Smart search exceptions
                (
                    "You may respond directly without searching for: greetings, clarifications "
                    "about previous responses, general knowledge questions, "
                    "or basic conversational exchanges."
                ),
                # Precision guidelines
                "When providing information from the knowledge base:",
                "- Use exact naming conventions and terminology found in the documentation",
                "- Only state what is explicitly documented - do not infer, assume, or extrapolate",
                "- If multiple interpretations exist, mention all documented options",
                "- Clearly distinguish between documented facts and general knowledge",
                # Handling search failures
                "If knowledge base search yields no relevant results:",
                "- Explicitly state that the information is not available in the knowledge base",
                "- Offer to help with related queries that might be documented",
                "- Do not provide speculative or general answers for domain-specific questions",
                # Response quality
                "Structure responses clearly with:",
                "- Direct answers to the user's question first",
                "- Supporting details from the knowledge base",
                "- Clear citations or references when possible",
                "- Actionable next steps if applicable",
                # Error handling
                (
                    "If the search tool fails or is unavailable, inform the user "
                    "about the limitation and suggest alternative ways to get the information."
                ),
            ]

            instructions = [default_instructions] + instructions

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
            telemetry=True,
            markdown=markdown,
            instructions=instructions,
            knowledge_filters=agent_knowledge_filters,
            model=model,
            db=self.db,  # Add database for history storage
            tools=[
                KnowledgeTools(
                    knowledge=knowledge,
                    enable_think=True,
                    enable_search=True,
                    enable_analyze=True,
                    add_instructions=True,
                    add_few_shot=True,
                )
            ],
        )

        logger.info(f"Successfully converted agent {db_agent.name}")
        return agno_agent

    async def convert_agents(
        self,
        db_agents: list[Agent],
        context: str = "default",
        continue_on_error: bool = True,
    ) -> list[AgnoAgent]:
        """
        Convert multiple agents with context-specific configuration.

        Args:
            db_agents: List of database agents to convert
            context: Context for conversion ('webhook', 'agent_os', 'default')
            continue_on_error: Whether to continue if one agent fails

        Returns:
            List of converted AgnoAgent instances
        """
        logger.info(f"Converting {len(db_agents)} agents for {context} context")

        # Set context-specific parameters
        if context == "webhook":
            markdown = True
            continue_on_error = True  # Always continue for webhooks
        elif context == "agent_os":
            markdown = False
            continue_on_error = False  # Fail fast for AgentOS
        else:
            markdown = False
            # Use provided continue_on_error parameter

        agno_agents = []
        for db_agent in db_agents:
            try:
                agno_agent = await self.convert_agent(
                    db_agent,
                    markdown=markdown,
                    search_knowledge=True,
                    add_history_to_context=True,
                    num_history_runs=3,
                    add_datetime_to_context=True,
                )
                agno_agents.append(agno_agent)
            except Exception as e:
                logger.error(f"Failed to convert {context} agent {db_agent.name}: {e}")
                if not continue_on_error:
                    raise
                # Continue processing other agents
                continue

        logger.info(f"Successfully converted {len(agno_agents)} {context} agents")
        return agno_agents

    async def convert_agents_for_webhook(self, db_agents: list[Agent]) -> list[AgnoAgent]:
        """Convert multiple agents for webhook processing - backward compatibility wrapper"""
        return await self.convert_agents(db_agents, context="webhook")

    async def convert_agents_for_agent_os(self, db_agents: list[Agent]) -> list[AgnoAgent]:
        """Convert multiple agents for AgentOS - backward compatibility wrapper"""
        return await self.convert_agents(db_agents, context="agent_os")
