"""Simple semantic cache for AI queries to save tokens.

Following CLAUDE.md: Single responsibility, boring solution, no premature abstractions.
"""

import hashlib
import math
import time
from typing import Any

from core.config import Config
from core.logger import get_module_logger
from openai import AsyncOpenAI


logger = get_module_logger(__name__)


class SemanticCacheService:
    """Simple in-memory semantic cache for AI responses."""

    def __init__(self, openai_client: AsyncOpenAI, config: Config) -> None:
        self._client = openai_client
        self._similarity_threshold = config.CACHE_SIMILARITY_THRESHOLD
        self._default_ttl = config.CACHE_DEFAULT_TTL
        self._embedding_model = config.CACHE_EMBEDDING_MODEL
        self._enabled = config.CACHE_ENABLED

        # Simple in-memory storage
        self._cache: dict[str, dict[str, Any]] = {}

    async def get_cached_response(self, query: str) -> str | None:
        """Get cached response if similar query exists."""
        if not self._enabled:
            return None

        try:
            self._cleanup_expired()

            if not self._cache:
                return None

            query_embedding = await self._generate_embedding(query)

            # Find most similar entry
            best_match = None
            best_similarity = 0.0

            for entry in self._cache.values():
                similarity = self._cosine_similarity(query_embedding, entry["embedding"])
                if similarity >= self._similarity_threshold and similarity > best_similarity:
                    best_match = entry
                    best_similarity = similarity

            if best_match:
                logger.debug(
                    f"Cache hit for query: {query[:50]}... (similarity: {best_similarity:.3f})"
                )
                return best_match["response"]

            return None

        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return None

    async def cache_response(self, query: str, response: str) -> bool:
        """Cache response for query."""
        if not self._enabled or not self._should_cache(query, response):
            return False

        try:
            query_embedding = await self._generate_embedding(query)

            cache_key = self._generate_key(query)
            entry = {
                "query": query,
                "response": response,
                "embedding": query_embedding,
                "timestamp": time.time(),
                "ttl_seconds": self._default_ttl,
            }

            self._cache[cache_key] = entry
            logger.debug(f"Cached response for query: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Cache store error: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("Cleared cache")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            "enabled": self._enabled,
            "entry_count": len(self._cache),
            "similarity_threshold": self._similarity_threshold,
            "default_ttl": self._default_ttl,
        }

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using OpenAI."""
        response = await self._client.embeddings.create(
            model=self._embedding_model, input=text.strip()
        )
        return response.data[0].embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between embeddings."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    def _should_cache(self, query: str, response: str) -> bool:
        """Simple policy: cache meaningful queries with good responses."""
        if not query.strip() or not response.strip():
            return False
        if len(query.strip()) < 10 or len(response.strip()) < 10:
            return False
        if any(word in response.lower() for word in ["error", "failed", "sorry"]):
            return False
        return True

    def _generate_key(self, query: str) -> str:
        """Generate cache key from query."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if current_time - entry["timestamp"] > entry["ttl_seconds"]
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
