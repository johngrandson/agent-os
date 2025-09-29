"""Core event system infrastructure"""

from .base import BaseEvent, BaseEventPublisher, EventPublisher
from .broker import app as faststream_app, broker, setup_broker_with_handlers
from .registry import EventRegistry


def register_all_domain_subscribers():
    """Register all domain subscribers with the event system"""
    # Import here to avoid circular imports
    import app.domains.agent_management.events.subscribers  # noqa: F401
    import app.domains.communication.messages.subscribers  # noqa: F401


__all__ = [
    "BaseEvent",
    "BaseEventPublisher",
    "EventPublisher",
    "EventRegistry",
    "broker",
    "faststream_app",
    "setup_broker_with_handlers",
    "register_all_domain_subscribers",
]
