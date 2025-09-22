"""
Event API schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.events.core import EventPriority
from app.events.types import EventType


class EventResponse(BaseModel):
    """Event response"""

    id: str = Field(..., description="Event ID")
    event_type: EventType = Field(..., description="Event type")
    timestamp: str = Field(..., description="Event timestamp")
    priority: EventPriority = Field(..., description="Event priority")
    source: Optional[str] = Field(None, description="Event source")
    target: Optional[str] = Field(None, description="Event target")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class EventListResponse(BaseModel):
    """Event list response"""

    events: List[EventResponse] = Field(..., description="List of events")
    total_count: int = Field(..., description="Total count")


class EventStatisticsResponse(BaseModel):
    """Event statistics response"""

    total_events: int = Field(..., description="Total events")
    recent_events_count: int = Field(..., description="Recent events count")
    by_type: Dict[str, int] = Field(..., description="Events by type")
    by_priority: Dict[str, int] = Field(..., description="Events by priority")
    by_source: Dict[str, int] = Field(..., description="Events by source")
    history_size: int = Field(..., description="Current history size")
    max_history_size: int = Field(..., description="Maximum history size")


class NotificationResponse(BaseModel):
    """Notification response"""

    id: str = Field(..., description="Notification ID")
    type: str = Field(..., description="Notification type")
    event_type: str = Field(..., description="Related event type")
    timestamp: str = Field(..., description="Notification timestamp")
    priority: str = Field(..., description="Notification priority")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Notification data")
    source: Optional[str] = Field(None, description="Notification source")
    target: Optional[str] = Field(None, description="Notification target")


class NotificationListResponse(BaseModel):
    """Notification list response"""

    notifications: List[NotificationResponse] = Field(
        ..., description="List of notifications"
    )
    total_count: int = Field(..., description="Total count")
