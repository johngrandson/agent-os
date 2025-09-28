"""
Abstract base class for cache backends.

Following CLAUDE.md: Single responsibility, clear interface, boring abstraction.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.infrastructure.cache.types import CacheEntry


class CacheBackend(ABC):
    """
    Abstract interface for cache storage backends.

    Provides pluggable storage abstraction for semantic cache service.
    All methods are async to support both sync and async backend implementations.
    """

    @abstractmethod
    async def store_entry(self, key: str, entry: CacheEntry) -> bool:
        """
        Store cache entry with TTL tracking.

        Args:
            key: Unique cache key
            entry: Cache entry containing response, embedding, metadata, and TTL

        Returns:
            True if stored successfully, False otherwise
        """
        pass

    @abstractmethod
    async def search_similar(
        self, embedding: list[float], threshold: float, limit: int = 10
    ) -> list[tuple[CacheEntry, float]]:
        """
        Search for similar entries by embedding similarity.

        Args:
            embedding: Query embedding vector
            threshold: Minimum similarity threshold (0.0 to 1.0)
            limit: Maximum number of results to return

        Returns:
            List of (entry, similarity_score) tuples, sorted by similarity descending
        """
        pass

    @abstractmethod
    async def invalidate(self, key: str) -> bool:
        """
        Remove specific entry by key.

        Args:
            key: Cache key to remove

        Returns:
            True if entry was removed, False if key not found
        """
        pass

    @abstractmethod
    async def clear_all(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if cleared successfully, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Return backend health status and metrics.

        Returns:
            Dictionary containing health information:
            - storage_healthy: bool
            - entry_count: int
            - backend_type: str
            - additional backend-specific metrics
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries based on TTL.

        Returns:
            Number of entries cleaned up
        """
        pass
