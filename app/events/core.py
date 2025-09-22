"""
Core event system contracts and base classes
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class EventPriority(str, Enum):
    """Event priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BaseEvent(BaseModel):
    """Base event model for all domain events"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(..., description="Type of event")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    priority: EventPriority = Field(default=EventPriority.NORMAL)
    source: Optional[str] = Field(None, description="Source of the event")
    target: Optional[str] = Field(None, description="Target of the event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        use_enum_values = True


class EventHandler(ABC):
    """Abstract event handler interface"""

    @abstractmethod
    async def handle(self, event: BaseEvent) -> None:
        """Handle an event"""
        pass

    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """Check if this handler can handle the event type"""
        pass
