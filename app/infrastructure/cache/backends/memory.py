"""
In-memory cache backend implementation.

Following CLAUDE.md: Single responsibility, extracted from service, boring solution.
Maintains exact same behavior as the embedded storage logic.
"""

import math
import time
from typing import Any

from app.infrastructure.cache.backends.base import CacheBackend
from app.infrastructure.cache.types import CacheEntry
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class MemoryBackend(CacheBackend):
    """
    Simple in-memory cache backend.

    Extracted from SemanticCacheService to provide pluggable storage.
    Preserves exact same behavior including TTL management and similarity search.
    """

    def __init__(self) -> None:
        """Initialize memory storage containers."""
        # Simple in-memory storage - same as original service
        self._storage: dict[str, CacheEntry] = {}
        self._timestamps: dict[str, float] = {}

    async def store_entry(self, key: str, entry: CacheEntry) -> bool:
        """
        Store cache entry with TTL tracking.

        Maintains exact same behavior as original service storage logic.
        """
        try:
            self._storage[key] = entry
            self._timestamps[key] = time.time()
            logger.debug(f"Stored entry in memory backend: {key}")
            return True
        except Exception as e:
            logger.error(f"Memory backend store error: {e}")
            return False

    async def search_similar(
        self, embedding: list[float], threshold: float, limit: int = 10
    ) -> list[tuple[CacheEntry, float]]:
        """
        Search for similar entries by embedding similarity.

        Extracted from _search_similar_entries - maintains exact same logic.
        """
        try:
            candidates = []

            for entry in self._storage.values():
                similarity = self._calculate_cosine_similarity(embedding, entry.embedding)
                if similarity >= threshold:
                    candidates.append((entry, similarity))

            # Sort by similarity (highest first) - same as original
            candidates.sort(key=lambda x: x[1], reverse=True)

            # Apply limit
            return candidates[:limit]

        except Exception as e:
            logger.error(f"Memory backend search error: {e}")
            return []

    async def invalidate(self, key: str) -> bool:
        """
        Remove specific entry by key.

        Maintains exact same behavior as original service invalidation.
        """
        try:
            if key in self._storage:
                del self._storage[key]
                del self._timestamps[key]
                logger.debug(f"Invalidated entry in memory backend: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Memory backend invalidation error: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        Clear all cache entries.

        Maintains exact same behavior as original service clear logic.
        """
        try:
            self._storage.clear()
            self._timestamps.clear()
            logger.debug("Cleared all entries from memory backend")
            return True
        except Exception as e:
            logger.error(f"Memory backend clear error: {e}")
            return False

    async def health_check(self) -> dict[str, Any]:
        """
        Return backend health status and metrics.

        Extracted from original service health check storage reporting.
        """
        try:
            return {
                "storage_healthy": True,
                "entry_count": len(self._storage),
                "backend_type": "memory",
                "timestamp_count": len(self._timestamps),
            }
        except Exception as e:
            logger.error(f"Memory backend health check error: {e}")
            return {
                "storage_healthy": False,
                "entry_count": 0,
                "backend_type": "memory",
                "error": str(e),
            }

    async def cleanup_expired(self) -> int:
        """
        Remove expired entries based on TTL.

        Extracted from _cleanup_expired - maintains exact same logic.
        """
        try:
            current_time = time.time()
            expired_keys = []

            for key, entry in self._storage.items():
                if entry.ttl_seconds is not None:
                    entry_time = self._timestamps.get(key, current_time)
                    if current_time - entry_time > entry.ttl_seconds:
                        expired_keys.append(key)

            # Remove expired entries
            for key in expired_keys:
                await self.invalidate(key)

            if expired_keys:
                logger.debug(f"Memory backend cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)

        except Exception as e:
            logger.error(f"Memory backend cleanup error: {e}")
            return 0

    def _calculate_cosine_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Extracted from service - maintains exact same calculation logic.
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimensions")

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2, strict=False))

        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(a * a for a in embedding2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Return cosine similarity
        return dot_product / (magnitude1 * magnitude2)
