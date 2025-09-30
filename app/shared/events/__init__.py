"""Core event system infrastructure"""

from .base import BaseEvent, BaseEventPublisher, EventPublisher
from .broker import app as faststream_app, broker, setup_broker_with_handlers
from .registry import EventRegistry


__all__ = [
    "BaseEvent",
    "BaseEventPublisher",
    "EventPublisher",
    "EventRegistry",
    "broker",
    "faststream_app",
    "setup_broker_with_handlers",
]
