"""
WebSocket API routes for real-time event streaming
"""

import json
import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional, List

from app.events.websocket import connection_manager
from app.events.types import EventType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, client_id: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time event streaming"""

    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())

    await connection_manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection",
                    "message": "Connected to event stream",
                    "client_id": client_id,
                }
            )
        )

        while True:
            # Listen for client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_client_message(client_id, message)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON format"})
                )
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Error processing message"})
                )

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        connection_manager.disconnect(client_id)


async def handle_client_message(client_id: str, message: dict):
    """Handle messages from WebSocket clients"""

    message_type = message.get("type")

    if message_type == "subscribe":
        # Subscribe to specific event types
        event_types = message.get("event_types", [])
        if event_types:
            connection_manager.subscribe_to_events(client_id, event_types)
            await connection_manager.send_personal_message(
                json.dumps(
                    {"type": "subscription_confirmed", "event_types": event_types}
                ),
                client_id,
            )

    elif message_type == "unsubscribe":
        # Unsubscribe from specific event types
        event_types = message.get("event_types", [])
        if event_types:
            connection_manager.unsubscribe_from_events(client_id, event_types)
            await connection_manager.send_personal_message(
                json.dumps(
                    {"type": "unsubscription_confirmed", "event_types": event_types}
                ),
                client_id,
            )

    elif message_type == "get_subscriptions":
        # Get current subscriptions
        subscriptions = list(connection_manager.get_client_subscriptions(client_id))
        await connection_manager.send_personal_message(
            json.dumps({"type": "subscriptions", "event_types": subscriptions}),
            client_id,
        )

    elif message_type == "ping":
        # Ping/pong for connection health check
        await connection_manager.send_personal_message(
            json.dumps({"type": "pong", "timestamp": message.get("timestamp")}),
            client_id,
        )

    else:
        await connection_manager.send_personal_message(
            json.dumps(
                {"type": "error", "message": f"Unknown message type: {message_type}"}
            ),
            client_id,
        )


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "active_connections": connection_manager.get_connection_count(),
        "available_event_types": [event_type.value for event_type in EventType],
    }
