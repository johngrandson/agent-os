"""
Semantic cache service implementation.

Following CLAUDE.md: Single responsibility, boring solution, no premature abstractions.
Consolidates embedder + similarity + policy with pluggable backend storage.
"""

import hashlib
from typing import Any

from app.infrastructure.cache.backends.base import CacheBackend
from app.infrastructure.cache.types import (
    CacheConfig,
    CacheEntry,
    CacheResult,
    CacheSearchResult,
)
from core.config import Config
from core.logger import get_module_logger
from openai import AsyncOpenAI


logger = get_module_logger(__name__)


class SemanticCacheService:
    """
    Simple semantic cache service with pluggable backend.

    Handles embedding generation, policy decisions, and delegates
    storage operations to backend interface.
    """

    def __init__(self, openai_client: AsyncOpenAI, config: Config, backend: CacheBackend) -> None:
        self._client = openai_client
        self._config = self._create_cache_config(config)
        self._backend = backend

        # Embedding model dimensions for validation
        self._embedding_dimensions = self._get_model_dimensions(self._config.embedding_model)

    async def get_cached_response(
        self, query: str, metadata: dict[str, Any] | None = None
    ) -> CacheSearchResult:
        """Get cached response for query if similar entry exists."""
        if not self._config.enabled:
            return CacheSearchResult(result=CacheResult.MISS)

        try:
            # Clean expired entries first
            await self._backend.cleanup_expired()

            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)

            # Search for similar entries using backend
            similar_entries = await self._backend.search_similar(
                query_embedding, self._config.similarity_threshold
            )

            if not similar_entries:
                logger.debug(f"Cache miss for query: {query[:50]}...")
                return CacheSearchResult(result=CacheResult.MISS)

            # Get best match
            best_match, similarity_score = similar_entries[0]

            logger.debug(
                f"Cache hit for query: {query[:50]}... (similarity: {similarity_score:.3f})"
            )
            return CacheSearchResult(
                result=CacheResult.HIT, entry=best_match, similarity_score=similarity_score
            )

        except Exception as e:
            logger.error(f"Cache search error: {e}")
            return CacheSearchResult(result=CacheResult.ERROR, error=str(e))

    async def cache_response(
        self, query: str, response: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Cache response for query if policy allows."""
        if not self._config.enabled:
            return False

        metadata = metadata or {}

        try:
            # Simple policy check
            if not self._should_cache(query, response, metadata):
                logger.debug(f"Policy rejected caching for query: {query[:50]}...")
                return False

            # Generate embedding
            query_embedding = await self._generate_embedding(query)

            # Create cache entry
            cache_key = self._generate_cache_key(query, metadata)
            ttl = self._get_ttl(metadata)

            entry = CacheEntry(
                key=cache_key,
                response=response,
                embedding=query_embedding,
                metadata=metadata,
                ttl_seconds=ttl,
            )

            # Store entry using backend
            success = await self._backend.store_entry(cache_key, entry)

            if success:
                logger.debug(f"Cached response for query: {query[:50]}...")
            return success

        except Exception as e:
            logger.error(f"Cache store error: {e}")
            return False

    async def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry."""
        if not self._config.enabled:
            return False

        try:
            success = await self._backend.invalidate(key)
            if success:
                logger.debug(f"Invalidated cache entry: {key}")
            return success
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False

    async def clear_cache(self) -> bool:
        """Clear entire cache."""
        if not self._config.enabled:
            return False

        try:
            success = await self._backend.clear_all()
            if success:
                logger.info("Cleared entire cache")
            return success
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def health_check(self) -> dict[str, Any]:
        """Check health of cache service."""
        health = {
            "enabled": self._config.enabled,
            "embedding_dimensions": self._embedding_dimensions,
            "config": {
                "similarity_threshold": self._config.similarity_threshold,
                "default_ttl": self._config.default_ttl,
                "backend": self._config.backend,
                "embedding_model": self._config.embedding_model,
            },
        }

        try:
            # Get backend health status
            backend_health = await self._backend.health_check()
            health.update(backend_health)

            # Test embedding generation
            await self._generate_embedding("health check test")
            health["embedding_healthy"] = True

        except Exception as e:
            logger.error(f"Health check error: {e}")
            health["error"] = str(e)
            health["embedding_healthy"] = False
            health["storage_healthy"] = False

        return health

    # Private helper methods

    def _create_cache_config(self, config: Config) -> CacheConfig:
        """Create cache configuration from app config."""
        return CacheConfig(
            enabled=config.CACHE_ENABLED,
            similarity_threshold=config.CACHE_SIMILARITY_THRESHOLD,
            default_ttl=config.CACHE_DEFAULT_TTL,
            embedding_model=config.CACHE_EMBEDDING_MODEL,
            backend=config.CACHE_BACKEND,
        )

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = await self._client.embeddings.create(
                model=self._config.embedding_model, input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    def _should_cache(self, query: str, response: str, metadata: dict[str, Any]) -> bool:
        """Simple policy: cache if response is not empty and query is meaningful."""
        # Don't cache empty responses
        if not response or not response.strip():
            return False

        # Don't cache very short queries (likely not useful)
        if len(query.strip()) < 10:
            return False

        # Don't cache if explicitly disabled in metadata
        if metadata.get("no_cache", False):
            return False

        return True

    def _get_ttl(self, metadata: dict[str, Any]) -> int:
        """Get TTL for cache entry in seconds."""
        # Check for explicit TTL in metadata
        if "cache_ttl" in metadata:
            return metadata["cache_ttl"]

        # Use default TTL
        return self._config.default_ttl

    def _generate_cache_key(self, query: str, metadata: dict[str, Any]) -> str:
        """Generate deterministic cache key from query and metadata."""
        # Create deterministic string from query and relevant metadata
        key_data = {
            "query": query,
            "metadata": {
                k: v for k, v in metadata.items() if k in ["agent_id", "model", "temperature"]
            },
        }
        key_string = str(sorted(key_data.items()))

        # Generate hash
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def _get_model_dimensions(self, model: str) -> int:
        """Get embedding dimensions for model."""
        # Known OpenAI embedding model dimensions
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return model_dimensions.get(model, 1536)  # Default to ada-002 dimensions
