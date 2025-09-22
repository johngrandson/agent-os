"""
WebSocket manager for real-time event broadcasting
"""

import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from app.events.core import BaseEvent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time event broadcasting"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # connection_id -> event_types

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        logger.info(f"WebSocket client {client_id} connected")

    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        logger.info(f"WebSocket client {client_id} disconnected")

    def subscribe_to_events(self, client_id: str, event_types: List[str]):
        """Subscribe a client to specific event types"""
        if client_id in self.subscriptions:
            self.subscriptions[client_id].update(event_types)
            logger.info(f"Client {client_id} subscribed to events: {event_types}")

    def unsubscribe_from_events(self, client_id: str, event_types: List[str]):
        """Unsubscribe a client from specific event types"""
        if client_id in self.subscriptions:
            self.subscriptions[client_id] -= set(event_types)
            logger.info(f"Client {client_id} unsubscribed from events: {event_types}")

    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast_event(self, event: BaseEvent):
        """Broadcast an event to all subscribed clients"""
        if not self.active_connections:
            return

        event_data = {
            "id": event.id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "priority": event.priority.value,
            "source": event.source,
            "target": event.target,
            "data": event.data,
            "metadata": event.metadata,
        }

        message = json.dumps(event_data)
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            # Check if client is subscribed to this event type
            client_subscriptions = self.subscriptions.get(client_id, set())
            if (
                not client_subscriptions
                or event.event_type.value in client_subscriptions
            ):
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def broadcast_notification(self, notification: dict):
        """Broadcast a notification to all connected clients"""
        if not self.active_connections:
            return

        message = json.dumps({"type": "notification", "data": notification})

        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting notification to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)

    def get_client_subscriptions(self, client_id: str) -> Set[str]:
        """Get the event types a client is subscribed to"""
        return self.subscriptions.get(client_id, set())


# Global connection manager instance
connection_manager = ConnectionManager()
