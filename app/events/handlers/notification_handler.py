"""
Notification event handler for real-time updates
"""

import logging
from typing import Set, Dict, Any
from app.events.core import BaseEvent, EventHandler, EventPriority
from app.events.types import EventType

logger = logging.getLogger(__name__)


class NotificationEventHandler(EventHandler):
    """Event handler that manages notifications for real-time updates"""

    def __init__(self):
        self.active_connections: Set[str] = set()  # WebSocket connections
        self.agent_subscriptions: Dict[str, Set[str]] = {}  # agent_id -> connection_ids
        self.notifications: list[Dict[str, Any]] = []
        self.max_notifications = 1000

    async def handle(self, event: BaseEvent) -> None:
        """Handle an event by creating notifications"""

        # Create notification from event
        notification = self._create_notification(event)

        # Add to notification history
        self._add_notification(notification)

        # Broadcast to relevant connections
        await self._broadcast_notification(notification, event)

    def can_handle(self, event_type: str) -> bool:
        """Handle specific event types that should create notifications"""
        notification_events = {
            EventType.AGENT_CREATED,
            EventType.AGENT_ACTIVATED,
            EventType.AGENT_DEACTIVATED,
            EventType.TOOL_EXECUTED,
            EventType.TOOL_FAILED,
            EventType.SYSTEM_ALERT,
            EventType.SYSTEM_ERROR,
        }
        return event_type in notification_events

    def _create_notification(self, event: BaseEvent) -> Dict[str, Any]:
        """Create a notification from an event"""

        notification = {
            "id": event.id,
            "type": "event_notification",
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "priority": event.priority,
            "title": self._get_notification_title(event),
            "message": self._get_notification_message(event),
            "data": event.data,
            "source": event.source,
            "target": event.target,
        }

        return notification

    def _get_notification_title(self, event: BaseEvent) -> str:
        """Get notification title based on event type"""

        title_map = {
            EventType.AGENT_CREATED: "Novo Agente Criado",
            EventType.AGENT_ACTIVATED: "Agente Ativado",
            EventType.AGENT_DEACTIVATED: "Agente Desativado",
            EventType.TOOL_EXECUTED: "Ferramenta Executada",
            EventType.TOOL_FAILED: "Falha na Ferramenta",
            EventType.SYSTEM_ALERT: "Alerta do Sistema",
            EventType.SYSTEM_ERROR: "Erro do Sistema",
        }

        return title_map.get(event.event_type, "Notificação")

    def _get_notification_message(self, event: BaseEvent) -> str:
        """Get notification message based on event"""

        if event.event_type == EventType.AGENT_CREATED:
            agent_id = getattr(event, "agent_id", "Unknown")
            return f"Novo agente criado: {agent_id}"

        elif event.event_type == EventType.TOOL_EXECUTED:
            tool_name = getattr(event, "tool_name", "Unknown")
            return f"Ferramenta {tool_name} executada"

        elif event.event_type == EventType.SYSTEM_ERROR:
            error = event.data.get("error", "Erro desconhecido")
            return f"Erro do sistema: {error}"

        else:
            return f"Evento: {event.event_type}"

    def _add_notification(self, notification: Dict[str, Any]) -> None:
        """Add notification to history"""
        self.notifications.append(notification)
        if len(self.notifications) > self.max_notifications:
            self.notifications.pop(0)

    async def _broadcast_notification(
        self, notification: Dict[str, Any], event: BaseEvent
    ) -> None:
        """Broadcast notification to relevant connections via WebSocket"""
        logger.info(f"Broadcasting notification: {notification['title']}")

        # Import here to avoid circular imports
        try:
            from app.events.websocket import connection_manager

            # Broadcast event to WebSocket connections
            await connection_manager.broadcast_event(event)

            # Also broadcast the notification
            await connection_manager.broadcast_notification(notification)

        except ImportError:
            logger.warning("WebSocket manager not available for broadcasting")
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")

    def _get_target_connections(self, event: BaseEvent) -> Set[str]:
        """Get connections that should receive this notification"""
        target_connections = set()

        # Broadcast to all connections for system events
        if event.event_type.startswith("system."):
            target_connections.update(self.active_connections)

        # Send to specific agent connections if target is specified
        if event.target and event.target in self.agent_subscriptions:
            target_connections.update(self.agent_subscriptions[event.target])

        # Send to all if no specific target
        if not target_connections and event.priority in [
            EventPriority.HIGH,
            EventPriority.URGENT,
        ]:
            target_connections.update(self.active_connections)

        return target_connections

    def add_connection(self, connection_id: str) -> None:
        """Add a WebSocket connection"""
        self.active_connections.add(connection_id)
        logger.info(f"Added connection: {connection_id}")

    def remove_connection(self, connection_id: str) -> None:
        """Remove a WebSocket connection"""
        self.active_connections.discard(connection_id)

        # Remove from agent subscriptions
        for agent_id, connections in self.agent_subscriptions.items():
            connections.discard(connection_id)

        logger.info(f"Removed connection: {connection_id}")

    def subscribe_agent(self, connection_id: str, agent_id: str) -> None:
        """Subscribe a connection to agent-specific events"""
        if agent_id not in self.agent_subscriptions:
            self.agent_subscriptions[agent_id] = set()

        self.agent_subscriptions[agent_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to agent {agent_id}")

    def get_recent_notifications(self, limit: int = 50) -> list[Dict[str, Any]]:
        """Get recent notifications"""
        return self.notifications[-limit:] if limit > 0 else self.notifications
