"""FastStream Redis broker configuration"""

from app.events.core.registry import event_registry
from core.config import get_config
from faststream import FastStream
from faststream.redis import RedisBroker


config = get_config()

# Create Redis broker
broker = RedisBroker(config.redis_url)

# Create FastStream app
app = FastStream(broker)


def setup_broker_with_handlers():
    """Setup broker with all registered domain handlers"""
    # Include all registered routers in the broker
    for router in event_registry.get_all_routers():
        broker.include_router(router)

    return broker
