"""
Webhook Agent Processor - processes messages using Agno agents
"""

import logging

from agno.agent import Agent as AgnoAgent
from app.agents.agent import Agent
from app.agents.repositories.agent_repository import AgentRepository
from app.events.webhooks.publisher import WebhookEventPublisher
from app.integrations.agno import AgnoAgentConverter


logger = logging.getLogger(__name__)


class WebhookAgentProcessor:
    """Processes webhook messages using loaded Agno agents"""

    def __init__(
        self,
        agent_repository: AgentRepository,
        event_publisher: WebhookEventPublisher,
        agno_agent_converter: AgnoAgentConverter,
    ):
        self.agent_repository = agent_repository
        self.event_publisher = event_publisher
        self.agno_agent_converter = agno_agent_converter

        # Agent storage
        self.loaded_agents: list[Agent] = []
        self.agno_agents: list[AgnoAgent] = []

    async def initialize_agents(self):
        """Initialize and load agents for webhook processing"""
        logger.info("Initializing agents for webhook processing...")

        # Get agents from database
        db_agents = await self.agent_repository.get_agents_by_status(status=True)
        logger.info(f"Found {len(db_agents)} active agents in database")

        # Filter for WhatsApp-enabled agents
        webhook_agents = [
            agent for agent in db_agents if agent.whatsapp_enabled and agent.whatsapp_token
        ]
        logger.info(f"Filtered to {len(webhook_agents)} WhatsApp-enabled agents")

        # Convert to AgnoAgent instances using integration layer
        self.agno_agents = await self.agno_agent_converter.convert_agents_for_webhook(
            webhook_agents
        )
        self.loaded_agents = webhook_agents

        logger.info(f"Successfully initialized {len(self.agno_agents)} webhook agents")

    async def process_message(self, agent_id: str, message: str, chat_id: str) -> str | None:
        """
        Process a message with the specified agent

        Args:
            agent_id: Agent UUID as string
            message: User message text
            chat_id: WhatsApp chat ID

        Returns:
            Agent response or None if processing failed
        """
        try:
            # Find the agent by ID
            target_agent = self.find_agno_agent_by_id(agent_id)
            if not target_agent:
                logger.error(f"Agent not found for webhook processing: {agent_id}")
                return None

            logger.info(f"Processing message with agent: {target_agent.name}")
            logger.debug(f"Message: {message}")
            logger.debug(f"Chat ID: {chat_id}")

            # Process the message with the agent
            response = await target_agent.arun(message)

            if response and hasattr(response, "content"):
                response_text = response.content
                logger.info(
                    f"Agent {target_agent.name} responded successfully. "
                    f"Response length: {len(response_text)}"
                )
                logger.debug(f"Response: {response_text}")
                return response_text
            logger.warning(f"Agent {target_agent.name} returned empty or invalid response")
            return None

        except Exception as e:
            logger.error(f"Error processing message with agent {agent_id}: {e}")
            return None

    def find_agno_agent_by_id(self, agent_id: str) -> AgnoAgent | None:
        """Find an AgnoAgent by ID"""
        for agno_agent in self.agno_agents:
            if agno_agent.id == agent_id:
                return agno_agent
        return None

    def get_loaded_agents(self) -> list[Agent]:
        """Get the loaded DB agents"""
        return self.loaded_agents.copy()

    def get_agno_agents(self) -> list[AgnoAgent]:
        """Get the AgnoAgent instances"""
        return self.agno_agents.copy()

    def has_agents(self) -> bool:
        """Check if agents are loaded"""
        return len(self.agno_agents) > 0

    async def reload_agents(self):
        """Reload agents from database"""
        logger.info("Reloading agents for webhook processing...")
        await self.initialize_agents()
