"""
Cached runtime agent implementation using decorator pattern.

Following CLAUDE.md: Boring decorator solution, single responsibility, transparent caching.
Wraps existing RuntimeAgent to add semantic cache without breaking existing APIs.
"""

from typing import Any

from app.infrastructure.cache import CacheResult, SemanticCacheService
from app.infrastructure.providers.base import RuntimeAgent
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class CachedRuntimeAgent(RuntimeAgent):
    """
    Decorator wrapper for RuntimeAgent that adds transparent semantic caching.

    Maintains full compatibility with RuntimeAgent interface while adding:
    - Cache hit: Returns cached response immediately
    - Cache miss: Calls original agent + stores result in cache
    - Error handling: Falls back to original agent if cache fails
    """

    def __init__(
        self,
        runtime_agent: RuntimeAgent,
        cache_service: SemanticCacheService,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialize cached runtime agent.

        Args:
            runtime_agent: Original runtime agent to wrap
            cache_service: Semantic cache service for storage/retrieval
            enable_cache: Whether to enable caching (allows runtime disable)
        """
        self._agent = runtime_agent
        self._cache = cache_service
        self._enable_cache = enable_cache

    async def arun(self, message: str) -> str:
        """
        Run agent with message, using cache transparently.

        Flow:
        1. Check cache if enabled
        2. Return cached response if hit
        3. Call original agent if miss
        4. Store response in cache
        5. Return response

        Args:
            message: Input message for the agent

        Returns:
            Agent response (from cache or fresh generation)
        """
        # If cache disabled, go straight to original agent
        if not self._enable_cache:
            return await self._agent.arun(message)

        try:
            # 1. Check cache first
            cache_metadata = self._create_cache_metadata()
            cache_result = await self._cache.get_cached_response(message, cache_metadata)

            # 2. Handle cache hit
            if cache_result.result == CacheResult.HIT and cache_result.entry:
                logger.debug(
                    f"Cache HIT for agent {self.id}: {message[:50]}... "
                    f"(similarity: {cache_result.similarity_score:.3f})"
                )
                return cache_result.entry.response

            # 3. Cache miss or error - call original agent
            logger.debug(f"Cache MISS for agent {self.id}: {message[:50]}...")

        except Exception as cache_error:
            # Cache failure - log and continue with original agent
            logger.warning(f"Cache lookup failed for agent {self.id}: {cache_error}")

        # 4. Get response from original agent
        try:
            response = await self._agent.arun(message)

            # 5. Store response in cache if enabled and valid
            if self._enable_cache and self._should_cache_response(message, response):
                try:
                    cache_metadata = self._create_cache_metadata()
                    await self._cache.cache_response(message, response, cache_metadata)
                    logger.debug(f"Cached response for agent {self.id}: {message[:50]}...")
                except Exception as store_error:
                    # Cache storage failure - log but don't fail the request
                    logger.warning(f"Cache storage failed for agent {self.id}: {store_error}")

            return response

        except Exception as agent_error:
            # Agent failure - bubble up the error
            logger.error(f"Agent {self.id} failed: {agent_error}")
            raise

    @property
    def id(self) -> str:
        """Delegate to wrapped agent."""
        return self._agent.id

    @property
    def name(self) -> str:
        """Delegate to wrapped agent."""
        return self._agent.name

    def get_wrapped_agent(self) -> RuntimeAgent:
        """
        Access to underlying agent for backwards compatibility.

        Returns:
            Original wrapped RuntimeAgent
        """
        return self._agent

    def is_cache_enabled(self) -> bool:
        """
        Check if caching is enabled for this agent.

        Returns:
            True if caching is enabled
        """
        return self._enable_cache

    def _create_cache_metadata(self) -> dict[str, Any]:
        """
        Create metadata for cache operations.

        Includes agent-specific information for cache key generation
        and policy decisions.

        Returns:
            Metadata dictionary for cache operations
        """
        return {
            "agent_id": self.id,
            "agent_name": self.name,
            # Note: Model and temperature would be added here if available
            # in the RuntimeAgent interface in the future
        }

    def _should_cache_response(self, message: str, response: str) -> bool:
        """
        Determine if response should be cached.

        Simple policy based on response quality and message characteristics.

        Args:
            message: Original input message
            response: Agent response

        Returns:
            True if response should be cached
        """
        # Don't cache empty responses
        if not response or not response.strip():
            return False

        # Don't cache very short responses (likely errors or insufficient)
        if len(response.strip()) < 10:
            return False

        # Don't cache very short messages (likely not meaningful)
        if len(message.strip()) < 5:
            return False

        # Don't cache error responses (basic heuristic)
        error_indicators = ["error", "failed", "exception", "sorry, i"]
        response_lower = response.lower().strip()
        if any(indicator in response_lower for indicator in error_indicators):
            return False

        return True
