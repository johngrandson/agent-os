"""Events module with entity-based architecture"""

# Import all domain modules to register their handlers
from . import agents, orchestration
from .broker import app as faststream_app, broker, setup_broker_with_handlers
from .core.registry import event_registry
from .domains.messages import handlers as messages


__all__ = [
    "broker",
    "faststream_app",
    "setup_broker_with_handlers",
    "event_registry",
    "agents",
    "orchestration",
    "messages",
]
