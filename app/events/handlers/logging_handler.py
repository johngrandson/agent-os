"""
Logging event handler for system monitoring
"""

import logging
from app.events.core import BaseEvent, EventHandler, EventPriority

logger = logging.getLogger(__name__)


class LoggingEventHandler(EventHandler):
    """Event handler that logs events for monitoring and debugging"""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    async def handle(self, event: BaseEvent) -> None:
        """Handle an event by logging it"""

        # Determine log level based on event priority
        log_level = self._get_log_level(event.priority)

        # Create log message
        message = self._format_event_message(event)

        # Log the event
        logger.log(
            log_level,
            message,
            extra={
                "event_id": event.id,
                "event_type": event.event_type,
                "event_priority": event.priority,
                "event_source": event.source,
                "event_target": event.target,
                "event_data": event.data,
            },
        )

    def can_handle(self, event_type: str) -> bool:
        """This handler can handle all event types"""
        return True

    def _get_log_level(self, priority: EventPriority) -> int:
        """Get logging level based on event priority"""
        priority_to_level = {
            EventPriority.LOW: logging.DEBUG,
            EventPriority.NORMAL: logging.INFO,
            EventPriority.HIGH: logging.WARNING,
            EventPriority.URGENT: logging.ERROR,
        }
        return priority_to_level.get(priority, logging.INFO)

    def _format_event_message(self, event: BaseEvent) -> str:
        """Format event into a readable log message"""

        base_msg = f"Event {event.event_type}"

        # Add source/target information
        if event.source:
            base_msg += f" from {event.source}"
        if event.target:
            base_msg += f" to {event.target}"

        # Add specific information based on event type
        if event.event_type.startswith("agent."):
            if "agent_id" in event.data:
                base_msg += f" (Agent: {event.data['agent_id']})"
            elif hasattr(event, "agent_id"):
                base_msg += f" (Agent: {event.agent_id})"

        elif event.event_type.startswith("tool."):
            if "tool_name" in event.data:
                base_msg += f" (Tool: {event.data['tool_name']})"
            elif hasattr(event, "tool_name"):
                base_msg += f" (Tool: {event.tool_name})"

        # Add error information for failures
        if "error" in event.data:
            base_msg += f" - Error: {event.data['error']}"

        # Add results summary for completions
        if "results" in event.data and event.event_type.endswith(".completed"):
            results = event.data["results"]
            if isinstance(results, dict) and "completed" in results:
                base_msg += " - Success"
            else:
                base_msg += " - With results"

        return base_msg
