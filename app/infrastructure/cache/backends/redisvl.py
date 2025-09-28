"""
RedisVL cache backend implementation for production vector storage.

Following CLAUDE.md: Single responsibility, boring solution, proper error handling.
Implements vector similarity search using RedisVL with graceful fallback patterns.
"""

import json
import time
from typing import Any

from app.infrastructure.cache.backends.base import CacheBackend
from app.infrastructure.cache.types import CacheEntry
from core.config import Config
from core.logger import get_module_logger
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema


logger = get_module_logger(__name__)


class RedisVLBackend(CacheBackend):
    """
    RedisVL-based cache backend for production vector storage.

    Provides efficient vector similarity search using Redis with HNSW algorithm.
    Implements graceful error handling with fallback strategies.
    """

    def __init__(self, redis_client: Any, config: Config) -> None:
        """
        Initialize RedisVL backend with Redis client and configuration.

        Args:
            redis_client: Redis client instance
            config: Application configuration
        """
        self._redis = redis_client
        self._config = config
        self._index: SearchIndex | None = None
        self._index_name = config.CACHE_REDIS_INDEX_NAME
        self._key_prefix = config.CACHE_REDIS_KEY_PREFIX

        # Vector dimensions and configuration from config
        self._vector_dims = getattr(config, "CACHE_VECTOR_DIMS", 1536)
        self._vector_algorithm = getattr(config, "CACHE_VECTOR_ALGORITHM", "HNSW")
        self._distance_metric = getattr(config, "CACHE_VECTOR_DISTANCE_METRIC", "COSINE")

    async def store_entry(self, key: str, entry: CacheEntry) -> bool:
        """
        Store cache entry with vector indexing.

        Args:
            key: Unique cache key
            entry: Cache entry containing response, embedding, metadata, and TTL

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Ensure index exists
            await self._ensure_index()
            if not self._index:
                logger.error("Vector index not available for storage")
                return False

            # Prepare Redis key
            redis_key = f"{self._key_prefix}{key}"

            # Prepare data for storage
            data = {
                "key": key,
                "response": entry.response,
                "metadata": json.dumps(entry.metadata),
                "embedding": entry.embedding,
                "ttl_seconds": entry.ttl_seconds or self._config.CACHE_DEFAULT_TTL,
                "created_at": time.time(),
            }

            # Store in Redis with vector indexing
            await self._redis.hset(redis_key, mapping=data)

            # Set TTL if specified
            if entry.ttl_seconds:
                await self._redis.expire(redis_key, entry.ttl_seconds)

            logger.debug(f"Stored entry in RedisVL backend: {key}")
            return True

        except Exception as e:
            logger.error(f"RedisVL backend store error: {e}")
            return False

    async def search_similar(
        self, embedding: list[float], threshold: float, limit: int = 10
    ) -> list[tuple[CacheEntry, float]]:
        """
        Search for similar entries using vector similarity.

        Args:
            embedding: Query embedding vector
            threshold: Minimum similarity threshold (0.0 to 1.0)
            limit: Maximum number of results to return

        Returns:
            List of (entry, similarity_score) tuples, sorted by similarity descending
        """
        try:
            # Ensure index exists
            await self._ensure_index()
            if not self._index:
                logger.error("Vector index not available for search")
                return []

            # Create vector query
            query = VectorQuery(
                vector=embedding,
                vector_field_name="embedding",
                return_fields=["key", "response", "metadata", "ttl_seconds", "created_at"],
                num_results=limit,
            )

            # Execute search
            results = await self._index.query(query)

            # Process results and filter by threshold
            candidates = []
            for result in results:
                # RedisVL returns cosine distance, convert to similarity
                distance = float(result.get("vector_score", 1.0))
                similarity = 1.0 - distance  # Convert distance to similarity

                if similarity >= threshold:
                    # Reconstruct cache entry
                    entry = CacheEntry(
                        key=result["key"],
                        response=result["response"],
                        embedding=embedding,  # Use query embedding for consistency
                        metadata=json.loads(result.get("metadata", "{}")),
                        ttl_seconds=int(result.get("ttl_seconds", self._config.CACHE_DEFAULT_TTL)),
                    )
                    candidates.append((entry, similarity))

            # Sort by similarity (highest first)
            candidates.sort(key=lambda x: x[1], reverse=True)

            logger.debug(
                f"RedisVL search found {len(candidates)} candidates above threshold {threshold}"
            )
            return candidates

        except Exception as e:
            logger.error(f"RedisVL backend search error: {e}")
            return []

    async def invalidate(self, key: str) -> bool:
        """
        Remove specific entry by key.

        Args:
            key: Cache key to remove

        Returns:
            True if entry was removed, False if key not found
        """
        try:
            redis_key = f"{self._key_prefix}{key}"
            result = await self._redis.delete(redis_key)

            if result > 0:
                logger.debug(f"Invalidated entry in RedisVL backend: {key}")
                return True
            return False

        except Exception as e:
            logger.error(f"RedisVL backend invalidation error: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            # Delete all keys with our prefix
            pattern = f"{self._key_prefix}*"
            keys = await self._redis.keys(pattern)

            if keys:
                await self._redis.delete(*keys)
                logger.debug(f"Cleared {len(keys)} entries from RedisVL backend")

            return True

        except Exception as e:
            logger.error(f"RedisVL backend clear error: {e}")
            return False

    async def health_check(self) -> dict[str, Any]:
        """
        Return backend health status and metrics.

        Returns:
            Dictionary containing health information
        """
        try:
            # Check Redis connection
            await self._redis.ping()

            # Count entries
            pattern = f"{self._key_prefix}*"
            keys = await self._redis.keys(pattern)
            entry_count = len(keys)

            # Check index status
            index_healthy = False
            try:
                await self._ensure_index()
                index_healthy = self._index is not None
            except Exception:
                pass

            return {
                "storage_healthy": True,
                "entry_count": entry_count,
                "backend_type": "redisvl",
                "index_healthy": index_healthy,
                "index_name": self._index_name,
                "vector_dims": self._vector_dims,
            }

        except Exception as e:
            logger.error(f"RedisVL backend health check error: {e}")
            return {
                "storage_healthy": False,
                "entry_count": 0,
                "backend_type": "redisvl",
                "index_healthy": False,
                "error": str(e),
            }

    async def cleanup_expired(self) -> int:
        """
        Remove expired entries based on TTL.

        Redis handles TTL automatically, so this mainly reports on cleanup.

        Returns:
            Number of entries cleaned up (estimated)
        """
        try:
            # Redis handles TTL automatically, but we can check for consistency
            pattern = f"{self._key_prefix}*"
            keys = await self._redis.keys(pattern)

            current_time = time.time()
            expired_count = 0

            for key in keys:
                try:
                    data = await self._redis.hgetall(key)
                    if not data:
                        continue

                    created_at = float(data.get("created_at", current_time))
                    ttl_seconds = int(data.get("ttl_seconds", self._config.CACHE_DEFAULT_TTL))

                    if current_time - created_at > ttl_seconds:
                        # This entry should have expired
                        expired_count += 1
                        await self._redis.delete(key)

                except Exception:
                    # Skip individual key errors
                    continue

            if expired_count > 0:
                logger.debug(f"RedisVL backend cleaned up {expired_count} expired entries")

            return expired_count

        except Exception as e:
            logger.error(f"RedisVL backend cleanup error: {e}")
            return 0

    async def _ensure_index(self) -> None:
        """
        Ensure vector index exists and is properly configured.

        Creates index if it doesn't exist, handles index recreation if needed.
        """
        if self._index is not None:
            return

        try:
            # Define vector index schema
            schema = IndexSchema.from_dict(
                {
                    "index": {
                        "name": self._index_name,
                        "prefix": self._key_prefix,
                        "storage_type": "hash",
                    },
                    "fields": [
                        {
                            "name": "key",
                            "type": "text",
                        },
                        {
                            "name": "response",
                            "type": "text",
                        },
                        {
                            "name": "metadata",
                            "type": "text",
                        },
                        {
                            "name": "embedding",
                            "type": "vector",
                            "attrs": {
                                "dims": self._vector_dims,
                                "algorithm": self._vector_algorithm,
                                "distance_metric": self._distance_metric,
                            },
                        },
                        {
                            "name": "ttl_seconds",
                            "type": "numeric",
                        },
                        {
                            "name": "created_at",
                            "type": "numeric",
                        },
                    ],
                }
            )

            # Create index
            self._index = SearchIndex(schema=schema, redis_client=self._redis)

            # Create index if it doesn't exist
            try:
                await self._index.create(overwrite=False)
                logger.debug(f"Created RedisVL index: {self._index_name}")
            except Exception:
                # Index might already exist, try to load it
                logger.debug(f"Using existing RedisVL index: {self._index_name}")

        except Exception as e:
            logger.error(f"Failed to ensure RedisVL index: {e}")
            self._index = None
            raise
