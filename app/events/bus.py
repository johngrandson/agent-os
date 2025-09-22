"""
Event bus for agent communication and system events
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from app.events.core import BaseEvent, EventHandler, EventPriority
from app.events.types import EventType

logger = logging.getLogger(__name__)


class EventBus:
    """Event bus for managing and dispatching events"""

    def __init__(self):
        self.handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[BaseEvent] = []
        self.max_history_size = 1000
        self.running = False

    def subscribe(
        self, event_type: EventType, handler: Callable[[BaseEvent], None]
    ) -> None:
        """Subscribe a function to an event type"""
        self.subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler to {event_type}")

    def unsubscribe(
        self, event_type: EventType, handler: Callable[[BaseEvent], None]
    ) -> None:
        """Unsubscribe a function from an event type"""
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            logger.info(f"Unsubscribed handler from {event_type}")

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler"""
        for event_type in EventType:
            self.handlers[event_type] = []
            self.subscribers[event_type] = []
            if handler.can_handle(event_type):
                self.handlers[event_type].append(handler)
                logger.info(
                    f"Registered handler {handler.__class__.__name__} for {event_type}"
                )

    def unregister_handler(self, handler: EventHandler) -> None:
        """Unregister an event handler"""
        for event_type, handler_list in self.handlers.items():
            if handler in handler_list:
                handler_list.remove(handler)
                logger.info(
                    f"Unregistered handler {handler.__class__.__name__} from {event_type}"
                )

    async def emit(self, event: BaseEvent) -> None:
        """Emit an event to all subscribers and handlers"""
        logger.info(f"Emitting event: {event.event_type} (ID: {event.id})")

        # Add to history
        self._add_to_history(event)

        # Handle urgent events immediately
        if event.priority == EventPriority.URGENT:
            await self._handle_event_immediate(event)
        else:
            await self._handle_event(event)

    async def _handle_event(self, event: BaseEvent) -> None:
        """Handle an event by dispatching to handlers and subscribers"""
        tasks = []

        # Dispatch to registered handlers
        for handler in self.handlers[event.event_type]:
            try:
                task = asyncio.create_task(handler.handle(event))
                tasks.append(task)
            except Exception as e:
                logger.error(
                    f"Error creating task for handler {handler.__class__.__name__}: {e}"
                )

        # Dispatch to function subscribers
        for subscriber in self.subscribers[event.event_type]:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    task = asyncio.create_task(subscriber(event))
                    tasks.append(task)
                else:
                    # Run sync function in thread pool
                    task = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(
                            None, subscriber, event
                        )
                    )
                    tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task for subscriber: {e}")

        # Execute all tasks
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error executing event handlers: {e}")

    async def _handle_event_immediate(self, event: BaseEvent) -> None:
        """Handle urgent events immediately without task creation"""
        # Handle with registered handlers
        for handler in self.handlers[event.event_type]:
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(
                    f"Error in urgent event handler {handler.__class__.__name__}: {e}"
                )

        # Handle with function subscribers
        for subscriber in self.subscribers[event.event_type]:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    # Run sync function
                    subscriber(event)
            except Exception as e:
                logger.error(f"Error in urgent event subscriber: {e}")

    def _add_to_history(self, event: BaseEvent) -> None:
        """Add event to history with size limit"""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)

    def get_event_history(
        self,
        *,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        target: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BaseEvent]:
        """Get event history with optional filtering"""
        events = self.event_history

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        if target:
            events = [e for e in events if e.target == target]
        if since:
            since_iso = since.isoformat()
            events = [e for e in events if e.timestamp >= since_iso]

        # Apply limit
        return events[-limit:] if limit > 0 else events

    def get_event_statistics(self) -> Dict[str, Any]:
        """Get statistics about events"""
        if not self.event_history:
            return {"total_events": 0}

        # Count by type
        type_counts = defaultdict(int)
        priority_counts = defaultdict(int)
        source_counts = defaultdict(int)

        for event in self.event_history:
            type_counts[event.event_type] += 1
            priority_counts[event.priority] += 1
            if event.source:
                source_counts[event.source] += 1

        # Get recent events (last hour)
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        recent_events = self.get_event_history(since=hour_ago)

        return {
            "total_events": len(self.event_history),
            "recent_events_count": len(recent_events),
            "by_type": dict(type_counts),
            "by_priority": dict(priority_counts),
            "by_source": dict(source_counts),
            "history_size": len(self.event_history),
            "max_history_size": self.max_history_size,
        }

    async def clear_history(self) -> None:
        """Clear event history"""
        self.event_history.clear()
        logger.info("Event history cleared")

    def start(self) -> None:
        """Start the event bus"""
        self.running = True
        logger.info("Event bus started")

    def stop(self) -> None:
        """Stop the event bus"""
        self.running = False
        logger.info("Event bus stopped")


# Global event bus instance
event_bus = EventBus()
