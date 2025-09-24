"""
Webhook Agent Processor - processes messages using shared AgentLoader
"""

import logging

from app.events.webhooks.publisher import WebhookEventPublisher


logger = logging.getLogger(__name__)


class WebhookAgentProcessor:
    """Processes webhook messages using shared agent loading"""

    def __init__(
        self,
        agent_loader,
        event_publisher: WebhookEventPublisher,
    ):
        self.agent_loader = agent_loader
        self.event_publisher = event_publisher

    async def initialize_agents(self):
        """Initialize and load agents for webhook processing"""
        await self.agent_loader.load_webhook_agents()
        logger.info(f"Initialized {len(self.agent_loader.agno_agents)} webhook agents")

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
            # Find the agent by ID using shared loader
            target_agent = self.agent_loader.find_agno_agent_by_id(agent_id)
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

    async def reload_agents(self):
        """Reload agents from database"""
        logger.info("Reloading agents for webhook processing...")
        await self.initialize_agents()
