"""
Webhook Agent Processor - processes messages with request-time filtering and semantic caching
"""

from typing import TYPE_CHECKING, Any

from app.domains.communication.messages.publisher import MessageEventPublisher
from app.initialization import AgentCache
from core.config import Config
from core.logger import get_module_logger


if TYPE_CHECKING:
    from app.infrastructure.cache import SemanticCacheService

logger = get_module_logger(__name__)


class WebhookAgentProcessor:
    """Processes webhook messages using request-time agent selection with semantic caching"""

    def __init__(
        self,
        agent_cache: AgentCache,
        event_publisher: MessageEventPublisher,
        cache_service: "SemanticCacheService",
        config: Config,
    ) -> None:
        self.agent_cache = agent_cache
        self.event_publisher = event_publisher
        self.cache_service = cache_service
        self.config = config

    def is_valid_for_webhook(self, agent_id: str) -> bool:
        """Check if agent is valid for webhook processing"""
        # Find the DB agent to check webhook fields
        db_agents = self.agent_cache.get_loaded_db_agents()

        for db_agent in db_agents:
            if str(db_agent.id) == agent_id:
                return bool(db_agent.is_active)

        return False

    def is_number_allowed(self, chat_id: str) -> bool:
        """Check if the sender number is allowed to receive responses."""
        allowed_numbers = self.config.allowed_whatsapp_numbers
        if not allowed_numbers:
            # If no specific numbers are configured, allow all numbers
            return True

        # Extract number from chat_id (remove any formatting)
        # Chat ID format: "5511999998888@c.us" or "5511966541327-1601684616@g.us"
        sender_number = chat_id.split("@")[0]

        # For group chats, extract the actual number before the dash
        if "-" in sender_number:
            sender_number = sender_number.split("-")[0]

        is_allowed = sender_number in allowed_numbers
        logger.info(
            f"Number {sender_number} is allowed: {is_allowed} (allowed list: {allowed_numbers})"
        )
        return is_allowed

    async def process_message(self, agent_id: str, message: str, chat_id: str) -> str | None:
        """
        Process a message with the specified agent, using semantic cache when available

        Args:
            agent_id: Agent UUID as string
            message: User message text
            chat_id: WhatsApp chat ID

        Returns:
            Agent response or None if processing failed
        """
        try:
            # Check if sender number is allowed to receive responses
            if not self.is_number_allowed(chat_id):
                logger.info(f"Ignoring message from unauthorized number: {chat_id}")
                return None

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

            # Try to get cached response first
            cached_response = None
            logger.info(f"Cache service available: {self.cache_service is not None}")

            if self.cache_service:
                try:
                    # Create cache key with agent context
                    cache_query = f"agent:{agent_id}|message:{message}"
                    cached_response = await self.cache_service.get_cached_response(cache_query)

                    if cached_response:
                        logger.info(
                            f"Cache HIT for agent {target_agent.name} - using cached response"
                        )
                        return cached_response
                    else:
                        logger.debug(
                            f"Cache MISS for agent {target_agent.name} - generating new response"
                        )
                except Exception as cache_error:
                    logger.warning(f"Cache lookup failed for agent {agent_id}: {cache_error}")

            # Process the message with the agent (cache miss or no cache)
            response: Any = await target_agent.arun(message)

            # Handle different response formats
            response_text: str | None = None

            if not response:
                response_text = None
            elif isinstance(response, str):
                # Direct string response
                response_text = response
            elif hasattr(response, "content"):
                # Object with content attribute
                response_text = str(response.content)
            else:
                # Try to convert to string
                response_text = str(response)

            if response_text and response_text.strip():
                logger.info(
                    f"Agent {target_agent.name} responded successfully. "
                    f"Response length: {len(response_text)}"
                )
                logger.debug(f"Response: {response_text}")

                # Cache the response if cache service is available
                if self.cache_service and cached_response is None:  # Only cache on new responses
                    try:
                        cache_query = f"agent:{agent_id}|message:{message}"
                        await self.cache_service.cache_response(cache_query, response_text)
                        logger.debug(f"Cached response for agent {target_agent.name}")
                    except Exception as cache_error:
                        logger.warning(f"Cache storage failed for agent {agent_id}: {cache_error}")

                return response_text

            logger.warning(f"Agent {target_agent.name} returned empty or invalid response")
            return None

        except Exception as e:
            logger.error(f"Error processing message with agent {agent_id}: {e}")
            return None
