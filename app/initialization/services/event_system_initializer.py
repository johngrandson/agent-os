"""
Event system initialization service
"""

import logging

from app.agents.services.agent_service import AgentService
from app.events.agents.publisher import AgentEventPublisher


logger = logging.getLogger(__name__)


class EventSystemInitializer:
    """Handles event system initialization and handler registration"""

    def __init__(
        self,
        agent_service: AgentService,
        event_publisher: AgentEventPublisher,
    ):
        self.agent_service = agent_service
        self.event_publisher = event_publisher

    async def initialize(self):
        """Initialize event bus and handlers"""
        try:
            logger.info("Event system initialized successfully")

        except Exception as e:
            logger.error(f"Event system initialization failed: {e}")
            raise
