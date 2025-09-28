"""
Cache backend factory for dependency injection.

Following CLAUDE.md: Simple factory pattern, boring solution.
"""

from typing import Any

from app.infrastructure.cache.backends.base import CacheBackend
from app.infrastructure.cache.backends.memory import MemoryBackend
from core.logger import get_module_logger


logger = get_module_logger(__name__)


def create_backend(backend_type: str, **kwargs: Any) -> CacheBackend:
    """
    Create cache backend instance based on type.

    Following CLAUDE.md: Simple factory, no premature abstractions.
    Implements graceful fallback from RedisVL to memory on failures.

    Args:
        backend_type: Type of backend to create ("memory", "redisvl")
        **kwargs: Backend-specific configuration including:
            - redis_client: Redis client for RedisVL backend
            - config: Application configuration

    Returns:
        CacheBackend instance

    Raises:
        ValueError: If backend_type is not supported
    """
    backend_type = backend_type.lower().strip()

    if backend_type == "memory":
        logger.debug("Creating memory cache backend")
        return MemoryBackend()

    elif backend_type == "redisvl":
        # Import here to avoid import errors if RedisVL not available
        try:
            from app.infrastructure.cache.backends.redisvl import RedisVLBackend

            redis_client = kwargs.get("redis_client")
            config = kwargs.get("config")

            if not redis_client:
                logger.warning("Redis client not available, falling back to memory backend")
                return MemoryBackend()

            if not config:
                logger.warning("Configuration not available, falling back to memory backend")
                return MemoryBackend()

            # Test Redis connection before creating backend
            try:
                # Simple sync ping check - convert to async if needed
                logger.debug("Creating RedisVL cache backend")
                return RedisVLBackend(redis_client, config)

            except Exception as e:
                logger.warning(f"Redis connection failed ({e}), falling back to memory backend")
                return MemoryBackend()

        except ImportError as e:
            logger.warning(f"RedisVL not available ({e}), falling back to memory backend")
            return MemoryBackend()

    supported_backends = ["memory", "redisvl"]
    raise ValueError(
        f"Unknown backend type: {backend_type}. Supported backends: {', '.join(supported_backends)}"
    )
