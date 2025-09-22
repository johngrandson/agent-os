"""
Event system initialization service
"""

import logging
from app.events.bus import event_bus
from app.events.handlers.logging_handler import LoggingEventHandler
from app.events.handlers.notification_handler import NotificationEventHandler
from app.agents.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class EventSystemInitializer:
    """Handles event system initialization and handler registration"""

    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service

    async def initialize(self):
        """Initialize event bus and handlers"""
        try:
            # Start event bus
            event_bus.start()

            # Register event handlers
            logging_handler = LoggingEventHandler()
            notification_handler = NotificationEventHandler()

            event_bus.register_handler(logging_handler)
            event_bus.register_handler(notification_handler)

            logger.info("Event system initialized successfully")

        except Exception as e:
            logger.error(f"Event system initialization failed: {e}")
            raise
