"""
Event API routers
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, Depends
from dependency_injector.wiring import inject, Provide

from app.events.api.schemas import (
    EventResponse,
    EventListResponse,
    EventStatisticsResponse,
    NotificationResponse,
    NotificationListResponse,
)
from app.container import ApplicationContainer as Container
from app.events.types import EventType
from app.events.bus import EventBus
from app.events.handlers.notification_handler import NotificationEventHandler

router = APIRouter(tags=["events"])


@router.get(
    "/events",
    response_model=EventListResponse,
    summary="Get event history",
    description="Get event history with optional filtering",
)
@inject
async def get_events(
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    source: Optional[str] = Query(None, description="Filter by event source"),
    target: Optional[str] = Query(None, description="Filter by event target"),
    hours_ago: Optional[int] = Query(None, description="Get events from X hours ago"),
    limit: int = Query(100, description="Maximum number of events", ge=1, le=1000),
    event_bus: EventBus = Depends(Provide[Container.event_bus]),
):
    """Get event history with filtering"""

    since = None
    if hours_ago:
        since = datetime.utcnow() - timedelta(hours=hours_ago)

    events = event_bus.get_event_history(
        event_type=event_type, source=source, target=target, since=since, limit=limit
    )

    event_responses = [
        EventResponse(
            id=event.id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            priority=event.priority,
            source=event.source,
            target=event.target,
            data=event.data,
            metadata=event.metadata,
        )
        for event in events
    ]

    return EventListResponse(events=event_responses, total_count=len(event_responses))


@router.get(
    "/events/statistics",
    response_model=EventStatisticsResponse,
    summary="Get event statistics",
    description="Get statistics about the event system",
)
@inject
async def get_event_statistics(
    event_bus: EventBus = Depends(Provide[Container.event_bus]),
):
    """Get event statistics"""
    stats = event_bus.get_event_statistics()
    return EventStatisticsResponse(**stats)


@router.post(
    "/events/clear",
    summary="Clear event history",
    description="Clear the event history (admin operation)",
)
@inject
async def clear_event_history(
    event_bus: EventBus = Depends(Provide[Container.event_bus]),
):
    """Clear event history"""
    await event_bus.clear_history()
    return {"message": "Event history cleared successfully"}


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="Get recent notifications",
    description="Get recent notifications from the notification handler",
)
@inject
async def get_notifications(
    limit: int = Query(
        50, description="Maximum number of notifications", ge=1, le=1000
    ),
    event_bus: EventBus = Depends(Provide[Container.event_bus]),
):
    """Get recent notifications"""

    # Get notification handler from event bus
    notification_handler = None
    for handlers in event_bus.handlers.values():
        for handler in handlers:
            if isinstance(handler, NotificationEventHandler):
                notification_handler = handler
                break
        if notification_handler:
            break

    if not notification_handler:
        return NotificationListResponse(notifications=[], total_count=0)

    notifications = notification_handler.get_recent_notifications(limit=limit)

    notification_responses = [
        NotificationResponse(**notification) for notification in notifications
    ]

    return NotificationListResponse(
        notifications=notification_responses, total_count=len(notification_responses)
    )


@router.get(
    "/events/types",
    response_model=List[str],
    summary="Get available event types",
    description="Get list of all available event types",
)
async def get_event_types():
    """Get available event types"""
    return [event_type.value for event_type in EventType]
