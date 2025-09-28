"""
Integration tests for cache system with different backends.

Following CLAUDE.md: Test behavior, not implementation. Focus on end-to-end functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.infrastructure.cache.backends.factory import create_backend
from app.infrastructure.cache.service import SemanticCacheService
from app.infrastructure.cache.types import CacheResult
from core.config import Config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    client = AsyncMock()
    # Mock embedding response
    embedding_response = MagicMock()
    embedding_response.data = [MagicMock()]
    embedding_response.data[0].embedding = [0.1] * 1536
    client.embeddings.create.return_value = embedding_response
    return client


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = MagicMock(spec=Config)
    config.CACHE_ENABLED = True
    config.CACHE_SIMILARITY_THRESHOLD = 0.8
    config.CACHE_DEFAULT_TTL = 3600
    config.CACHE_MIN_QUERY_LENGTH = 10
    config.CACHE_MAX_RESPONSE_LENGTH = 5000
    config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"
    config.CACHE_BACKEND = "memory"
    return config


class TestCacheIntegrationMemoryBackend:
    """Test cache system end-to-end with memory backend"""

    async def test_cache_service_with_memory_backend_store_and_retrieve(
        self, mock_openai_client, mock_config
    ):
        """Test complete cache flow with memory backend"""
        # Create service with memory backend
        backend = create_backend("memory")
        service = SemanticCacheService(
            openai_client=mock_openai_client, config=mock_config, backend=backend
        )

        # Test store and retrieve flow
        query = "What is machine learning?"
        response = "Machine learning is a subset of AI..."
        metadata = {"model": "gpt-4", "temperature": 0.7}

        # Cache the response
        await service.cache_response(query, response, metadata)

        # Retrieve from cache
        cached_result = await service.get_cached_response(query, metadata)

        assert cached_result.result == CacheResult.HIT
        assert cached_result.entry is not None
        assert cached_result.entry.response == response
        assert cached_result.entry.metadata == metadata

    async def test_cache_service_with_memory_backend_health_check(
        self, mock_openai_client, mock_config
    ):
        """Test health check with memory backend"""
        backend = create_backend("memory")
        service = SemanticCacheService(
            openai_client=mock_openai_client, config=mock_config, backend=backend
        )

        health = await service.health_check()

        assert health["cache_enabled"] is True
        assert health["storage_healthy"] is True
        assert health["backend_type"] == "memory"


class TestCacheIntegrationRedisVLBackend:
    """Test cache system end-to-end with RedisVL backend (fallback behavior)"""

    async def test_cache_service_with_redisvl_backend_fallback(
        self, mock_openai_client, mock_config
    ):
        """Test cache service falls back to memory when RedisVL not available"""
        # Try to create RedisVL backend (should fallback to memory)
        backend = create_backend("redisvl", redis_client=MagicMock(), config=mock_config)
        service = SemanticCacheService(
            openai_client=mock_openai_client, config=mock_config, backend=backend
        )

        # Should still work with fallback backend
        query = "What is machine learning?"
        response = "Machine learning is a subset of AI..."
        metadata = {"model": "gpt-4", "temperature": 0.7}

        # Cache the response
        await service.cache_response(query, response, metadata)

        # Retrieve from cache
        cached_result = await service.get_cached_response(query, metadata)

        assert cached_result.result == CacheResult.HIT
        assert cached_result.entry is not None
        assert cached_result.entry.response == response

    async def test_cache_service_with_redisvl_backend_health_check(
        self, mock_openai_client, mock_config
    ):
        """Test health check with RedisVL backend (fallback)"""
        backend = create_backend("redisvl", redis_client=MagicMock(), config=mock_config)
        service = SemanticCacheService(
            openai_client=mock_openai_client, config=mock_config, backend=backend
        )

        health = await service.health_check()

        assert health["cache_enabled"] is True
        assert health["storage_healthy"] is True
        # Should report memory backend due to fallback
        assert health["backend_type"] == "memory"


class TestCacheBackendFactory:
    """Test backend factory configuration-driven selection"""

    def test_backend_factory_supports_memory(self):
        """Test factory creates memory backend"""
        backend = create_backend("memory")

        assert backend is not None
        assert type(backend).__name__ == "MemoryBackend"

    def test_backend_factory_supports_redisvl_fallback(self):
        """Test factory falls back to memory for RedisVL when no Redis client provided"""
        # Test fallback when missing redis_client (one of the required dependencies)
        backend = create_backend("redisvl", config=MagicMock())

        assert backend is not None
        # Should fallback to memory backend when redis_client is missing
        assert type(backend).__name__ == "MemoryBackend"

    def test_backend_factory_case_insensitive(self):
        """Test factory is case insensitive"""
        backend1 = create_backend("MEMORY")
        backend2 = create_backend("memory")
        backend3 = create_backend("Memory")

        assert type(backend1).__name__ == "MemoryBackend"
        assert type(backend2).__name__ == "MemoryBackend"
        assert type(backend3).__name__ == "MemoryBackend"

    def test_backend_factory_unknown_type_raises_error(self):
        """Test factory raises error for unknown backend types"""
        with pytest.raises(ValueError) as exc_info:
            create_backend("unknown_backend")

        assert "Unknown backend type" in str(exc_info.value)
        assert "Supported backends: memory, redisvl" in str(exc_info.value)


class TestCacheServiceConfig:
    """Test cache service respects configuration"""

    async def test_cache_service_disabled_by_config(self, mock_openai_client, mock_config):
        """Test cache service respects disabled configuration"""
        mock_config.CACHE_ENABLED = False

        backend = create_backend("memory")
        service = SemanticCacheService(
            openai_client=mock_openai_client, config=mock_config, backend=backend
        )

        query = "What is machine learning?"
        response = "Machine learning is a subset of AI..."
        metadata = {"model": "gpt-4"}

        # Should not cache when disabled
        await service.cache_response(query, response, metadata)

        # Should return miss when disabled
        cached_result = await service.get_cached_response(query, metadata)
        assert cached_result.result == CacheResult.MISS

    async def test_cache_service_threshold_respected(self, mock_openai_client, mock_config):
        """Test cache service respects similarity threshold"""
        mock_config.CACHE_SIMILARITY_THRESHOLD = 0.95  # Very high threshold

        backend = create_backend("memory")
        service = SemanticCacheService(
            openai_client=mock_openai_client, config=mock_config, backend=backend
        )

        # Cache one query
        query1 = "What is machine learning and how does it work?"
        response1 = "Machine learning is a subset of AI..."
        await service.cache_response(query1, response1, {})

        # Similar but not identical query (will have similarity < 0.95)
        query2 = "What is machine learning?"
        cached_result = await service.get_cached_response(query2, {})

        # Should return miss due to high threshold
        assert cached_result.result == CacheResult.MISS
