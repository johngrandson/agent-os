"""
Webhook Agent Processor - processes messages with request-time filtering
"""

from typing import Any

from app.events.domains.messages.publisher import MessageEventPublisher
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class WebhookAgentProcessor:
    """Processes webhook messages using request-time agent selection"""

    def __init__(
        self,
        agent_cache: Any,
        event_publisher: MessageEventPublisher,
    ) -> None:
        self.agent_cache = agent_cache
        self.event_publisher = event_publisher

    def is_valid_for_webhook(self, agent_id: str) -> bool:
        """Check if agent is valid for webhook processing"""
        # Find the DB agent to check webhook fields
        db_agents = self.agent_cache.get_loaded_db_agents()

        for db_agent in db_agents:
            if str(db_agent.id) == agent_id:
                return bool(db_agent.is_active)

        return False

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
            # Validate agent is suitable for webhook processing
            if not self.is_valid_for_webhook(agent_id):
                logger.error(f"Agent {agent_id} is not enabled for webhook processing")
                return None

            # Find the agent by ID
            target_agent = self.agent_cache.find_agent_by_id(agent_id)
            if not target_agent:
                logger.error(f"Agent not found: {agent_id}")
                return None

            logger.info(f"Processing message with agent: {target_agent.name}")
            logger.debug(f"Message: {message}")
            logger.debug(f"Chat ID: {chat_id}")

            # Process the message with the agent
            response = await target_agent.arun(message)

            if response and hasattr(response, "content"):
                response_text = str(response.content)
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
