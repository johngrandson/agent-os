"""Event domains package"""

# Import domain subscribers to register them
from .agents import subscribers as agents
from .messages import subscribers as messages


__all__ = ["agents", "messages"]
