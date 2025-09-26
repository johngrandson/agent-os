"""
Agno provider implementation - wraps existing agno functionality.
Following CLAUDE.md: boring wrapper, don't rewrite existing code.
"""

import logging

from agno.agent import Agent as AgnoAgent
from agno.os import AgentOS
from app.agents.agent import Agent
from app.providers.agno.agent_converter import AgnoAgentConverter
from app.providers.agno.knowledge_adapter import AgnoKnowledgeAdapter
from app.providers.agno.model_factory import AgnoModelFactory
from app.providers.base import AgentProvider, RuntimeAgent
from core.config import get_config

from fastapi import FastAPI


logger = logging.getLogger(__name__)


class AgnoRuntimeAgent(RuntimeAgent):
    """Simple wrapper around AgnoAgent to implement RuntimeAgent interface"""

    def __init__(self, agno_agent: AgnoAgent):
        self._agno_agent = agno_agent

    async def arun(self, message: str) -> str:
        """Run the agno agent with a message"""
        result = await self._agno_agent.arun(input=message)
        # Handle different return types from agno - get content as string
        if hasattr(result, "content"):
            return result.content
        if isinstance(result, str):
            return result
        return str(result)

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
        # Create required dependencies
        config = get_config()

        # Create knowledge adapter
        knowledge_adapter = AgnoKnowledgeAdapter(
            db_url=config.AGNO_DB_URL,
            event_publisher=None,  # Not needed for basic functionality
        )

        # Create model factory
        model_factory = AgnoModelFactory(config=config)

        # Create agno converter with dependencies
        self.agno_agent_converter = AgnoAgentConverter(
            knowledge_adapter=knowledge_adapter, model_factory=model_factory
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
