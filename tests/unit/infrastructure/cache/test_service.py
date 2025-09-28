"""
Tests for simplified semantic cache service.

Following CLAUDE.md: Test behavior, not implementation. One assertion per test when possible.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.infrastructure.cache.backends.memory import MemoryBackend
from app.infrastructure.cache.service import SemanticCacheService
from app.infrastructure.cache.types import CacheEntry, CacheResult
from core.config import Config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    client = AsyncMock()
    client.embeddings.create = AsyncMock()
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


@pytest.fixture
def memory_backend():
    """Create memory backend for testing"""
    return MemoryBackend()


@pytest.fixture
def cache_service(mock_openai_client, mock_config, memory_backend):
    """Create cache service for testing with memory backend"""
    return SemanticCacheService(
        openai_client=mock_openai_client, config=mock_config, backend=memory_backend
    )


class TestSemanticCacheService:
    """Test semantic cache service behavior following TDD principles."""

    # Core Cache Operations Tests

    @pytest.mark.asyncio
    async def test_should_return_miss_when_cache_is_empty(self, cache_service, mock_openai_client):
        """When cache is empty, should return MISS result for any query"""
        # Arrange
        mock_openai_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3])
        ]

        # Act
        result = await cache_service.get_cached_response("test query")

        # Assert
        assert result.result == CacheResult.MISS
        assert result.entry is None

    @pytest.mark.asyncio
    async def test_should_store_and_retrieve_exact_match(self, cache_service, mock_openai_client):
        """When storing and retrieving exact same query, should return HIT with same response"""
        # Arrange
        query = "test query for caching"
        response = "test response"
        embedding = [0.1, 0.2, 0.3]
        mock_openai_client.embeddings.create.return_value.data = [MagicMock(embedding=embedding)]

        # Act - Store
        store_success = await cache_service.cache_response(query, response)

        # Act - Retrieve
        retrieve_result = await cache_service.get_cached_response(query)

        # Assert
        assert store_success is True
        assert retrieve_result.result == CacheResult.HIT
        assert retrieve_result.entry.response == response

    # Similarity-Based Retrieval Tests

    @pytest.mark.asyncio
    async def test_should_return_hit_when_query_exceeds_similarity_threshold(
        self, cache_service, mock_openai_client
    ):
        """When query embedding similarity exceeds threshold,
        should return HIT with cached response"""
        # Arrange
        query1 = "what is the weather today"
        query2 = "how is the weather today"
        response = "It's sunny"
        # Embeddings with high cosine similarity (> 0.8 threshold)
        embedding1 = [0.9, 0.1, 0.0]
        embedding2 = [0.95, 0.05, 0.0]

        mock_openai_client.embeddings.create.side_effect = [
            MagicMock(data=[MagicMock(embedding=embedding1)]),  # For storing
            MagicMock(data=[MagicMock(embedding=embedding2)]),  # For retrieving
        ]

        # Act - Store first query
        await cache_service.cache_response(query1, response)

        # Act - Query with similar text
        result = await cache_service.get_cached_response(query2)

        # Assert
        assert result.result == CacheResult.HIT
        assert result.entry.response == response
        assert result.similarity_score > 0.8

    @pytest.mark.asyncio
    async def test_should_return_miss_when_query_below_similarity_threshold(
        self, cache_service, mock_openai_client
    ):
        """When query embedding similarity is below threshold, should return MISS"""
        # Arrange
        query1 = "what is the weather today"
        query2 = "how to cook pasta"
        response = "It's sunny"
        # Embeddings with low cosine similarity (< 0.8 threshold)
        embedding1 = [0.9, 0.1, 0.0]
        embedding2 = [0.1, 0.0, 0.9]

        mock_openai_client.embeddings.create.side_effect = [
            MagicMock(data=[MagicMock(embedding=embedding1)]),  # For storing
            MagicMock(data=[MagicMock(embedding=embedding2)]),  # For retrieving
        ]

        # Act - Store first query
        await cache_service.cache_response(query1, response)

        # Act - Query with dissimilar text
        result = await cache_service.get_cached_response(query2)

        # Assert
        assert result.result == CacheResult.MISS
        assert result.entry is None

    # Cache Configuration Tests

    @pytest.mark.asyncio
    async def test_should_return_miss_when_cache_is_disabled(self, mock_openai_client):
        """When cache is disabled in configuration, should return MISS without checking storage"""
        # Arrange - create service with disabled config
        disabled_config = MagicMock(spec=Config)
        disabled_config.CACHE_ENABLED = False
        disabled_config.CACHE_SIMILARITY_THRESHOLD = 0.8
        disabled_config.CACHE_DEFAULT_TTL = 3600
        disabled_config.CACHE_MIN_QUERY_LENGTH = 10
        disabled_config.CACHE_MAX_RESPONSE_LENGTH = 5000
        disabled_config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"
        disabled_config.CACHE_BACKEND = "memory"

        disabled_service = SemanticCacheService(
            openai_client=mock_openai_client, config=disabled_config, backend=MemoryBackend()
        )

        # Act
        result = await disabled_service.get_cached_response("test query")

        # Assert
        assert result.result == CacheResult.MISS
        assert result.entry is None

    @pytest.mark.asyncio
    async def test_should_not_store_when_cache_is_disabled(self, mock_openai_client):
        """When cache is disabled in configuration, should not store responses"""
        # Arrange - create service with disabled config
        disabled_config = MagicMock(spec=Config)
        disabled_config.CACHE_ENABLED = False
        disabled_config.CACHE_SIMILARITY_THRESHOLD = 0.8
        disabled_config.CACHE_DEFAULT_TTL = 3600
        disabled_config.CACHE_MIN_QUERY_LENGTH = 10
        disabled_config.CACHE_MAX_RESPONSE_LENGTH = 5000
        disabled_config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"
        disabled_config.CACHE_BACKEND = "memory"

        disabled_service = SemanticCacheService(
            openai_client=mock_openai_client, config=disabled_config, backend=MemoryBackend()
        )

        # Act
        result = await disabled_service.cache_response("test query", "test response")

        # Assert
        assert result is False

    # Cache Policy Tests

    @pytest.mark.asyncio
    async def test_should_not_cache_queries_below_minimum_length(self, cache_service):
        """When query is shorter than minimum length, should not cache response"""
        # Arrange
        short_query = "hi"  # Less than 10 character minimum
        response = "hello"

        # Act
        result = await cache_service.cache_response(short_query, response)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_should_not_cache_empty_responses(self, cache_service):
        """When response is empty or whitespace only, should not cache"""
        # Arrange
        query = "test query"

        # Act & Assert - Empty response
        result_empty = await cache_service.cache_response(query, "")
        assert result_empty is False

        # Act & Assert - Whitespace only response
        result_whitespace = await cache_service.cache_response(query, "   ")
        assert result_whitespace is False

    # TODO: Add test for max response length policy when implemented
    # The service currently doesn't implement max response length checking

    # Cache Management Tests

    @pytest.mark.asyncio
    async def test_should_invalidate_specific_cache_entry_by_key(
        self, cache_service, mock_openai_client
    ):
        """When invalidating by cache key, should remove specific entry from cache"""
        # Arrange
        query = "test query for invalidation"
        response = "test response"
        embedding = [0.1, 0.2, 0.3]

        mock_openai_client.embeddings.create.return_value.data = [MagicMock(embedding=embedding)]

        # Store entry
        await cache_service.cache_response(query, response)

        # Verify entry exists
        cached_result = await cache_service.get_cached_response(query)
        assert cached_result.result == CacheResult.HIT

        # Generate cache key for invalidation
        cache_key = cache_service._generate_cache_key(query, {})

        # Act - Invalidate
        success = await cache_service.invalidate(cache_key)

        # Assert - Entry should be removed
        assert success is True
        cached_after = await cache_service.get_cached_response(query)
        assert cached_after.result == CacheResult.MISS
        assert cached_after.entry is None

    @pytest.mark.asyncio
    async def test_should_clear_all_cache_entries(self, cache_service, mock_openai_client):
        """When clearing cache, should remove all stored entries"""
        # Arrange
        embedding = [0.1, 0.2, 0.3]
        mock_openai_client.embeddings.create.return_value.data = [MagicMock(embedding=embedding)]

        # Store multiple entries
        await cache_service.cache_response("query1", "response1")
        await cache_service.cache_response("query2", "response2")

        # Act - Clear cache
        success = await cache_service.clear_cache()

        # Assert - All entries should be removed
        assert success is True
        result1 = await cache_service.get_cached_response("query1")
        result2 = await cache_service.get_cached_response("query2")
        assert result1.result == CacheResult.MISS
        assert result1.entry is None
        assert result2.result == CacheResult.MISS
        assert result2.entry is None

    # Health Check Tests

    @pytest.mark.asyncio
    async def test_should_return_healthy_status_when_cache_enabled(self, cache_service):
        """When cache is enabled and working, health check should return healthy status"""
        # Act
        health = await cache_service.health_check()

        # Assert - Basic health indicators
        assert health["enabled"] is True
        assert "entry_count" in health
        assert "config" in health
        assert "embedding_healthy" in health
        assert health["embedding_healthy"] is True
        assert health["storage_healthy"] is True

    @pytest.mark.asyncio
    async def test_should_return_disabled_status_when_cache_disabled(self, mock_openai_client):
        """When cache is disabled in configuration, health check should reflect disabled status"""
        # Arrange - create service with disabled config
        disabled_config = MagicMock(spec=Config)
        disabled_config.CACHE_ENABLED = False
        disabled_config.CACHE_SIMILARITY_THRESHOLD = 0.8
        disabled_config.CACHE_DEFAULT_TTL = 3600
        disabled_config.CACHE_MIN_QUERY_LENGTH = 10
        disabled_config.CACHE_MAX_RESPONSE_LENGTH = 5000
        disabled_config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"
        disabled_config.CACHE_BACKEND = "memory"

        disabled_service = SemanticCacheService(
            openai_client=mock_openai_client, config=disabled_config, backend=MemoryBackend()
        )

        # Act
        health = await disabled_service.health_check()

        # Assert
        assert health["enabled"] is False

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_should_return_error_when_embedding_generation_fails(
        self, cache_service, mock_openai_client
    ):
        """When OpenAI embedding generation fails,
        should return ERROR result without raising exception"""
        # Arrange
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")

        # Act
        result = await cache_service.get_cached_response("test query")

        # Assert - Should handle error gracefully
        assert result.result == CacheResult.ERROR
        assert result.entry is None
        assert "API Error" in result.error

    # Similarity Calculation Tests

    @pytest.mark.asyncio
    async def test_should_calculate_perfect_similarity_for_identical_vectors(self, memory_backend):
        """When vectors are identical, cosine similarity should be 1.0"""
        # Arrange
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        # Act
        similarity = memory_backend._calculate_cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_should_calculate_zero_similarity_for_orthogonal_vectors(self, memory_backend):
        """When vectors are orthogonal, cosine similarity should be 0.0"""
        # Arrange
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        # Act
        similarity = memory_backend._calculate_cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - 0.0) < 0.001

    # Metadata Handling Tests

    @pytest.mark.asyncio
    async def test_should_store_and_retrieve_cache_with_metadata(
        self, cache_service, mock_openai_client
    ):
        """When caching with metadata, should store metadata and retrieve it with response"""
        # Arrange
        query = "test query with metadata"
        response = "test response"
        metadata = {"agent_id": "123", "model": "gpt-4"}
        embedding = [0.1, 0.2, 0.3]

        mock_openai_client.embeddings.create.return_value.data = [MagicMock(embedding=embedding)]

        # Act - Store with metadata
        store_success = await cache_service.cache_response(query, response, metadata)

        # Act - Retrieve with same metadata
        retrieve_result = await cache_service.get_cached_response(query, metadata)

        # Assert
        assert store_success is True
        assert retrieve_result.result == CacheResult.HIT
        assert retrieve_result.entry.response == response
        assert retrieve_result.entry.metadata == metadata

    @pytest.mark.asyncio
    async def test_should_not_cache_when_no_cache_metadata_flag_set(
        self, cache_service, mock_openai_client
    ):
        """When metadata contains no_cache flag, should not cache response"""
        # Arrange
        query = "test query with no cache flag"
        response = "test response"
        metadata = {"no_cache": True, "agent_id": "123"}

        # Act
        result = await cache_service.cache_response(query, response, metadata)

        # Assert
        assert result is False

    # Edge Cases and Additional Scenarios

    @pytest.mark.asyncio
    async def test_should_handle_none_metadata_gracefully(self, cache_service, mock_openai_client):
        """When metadata is None, should handle gracefully and use empty metadata"""
        # Arrange
        query = "test query with none metadata"
        response = "test response"
        embedding = [0.1, 0.2, 0.3]

        mock_openai_client.embeddings.create.return_value.data = [MagicMock(embedding=embedding)]

        # Act - Store with None metadata
        store_success = await cache_service.cache_response(query, response, None)

        # Act - Retrieve with None metadata
        retrieve_result = await cache_service.get_cached_response(query, None)

        # Assert
        assert store_success is True
        assert retrieve_result.result == CacheResult.HIT
        assert retrieve_result.entry.response == response
        assert retrieve_result.entry.metadata == {}

    @pytest.mark.asyncio
    async def test_should_return_false_when_invalidating_nonexistent_key(self, cache_service):
        """When invalidating a key that doesn't exist, should return False"""
        # Act
        result = await cache_service.invalidate("nonexistent_key")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_should_handle_zero_magnitude_vectors_in_similarity_calculation(
        self, memory_backend
    ):
        """When one vector has zero magnitude, cosine similarity should return 0.0"""
        # Arrange
        vec1 = [1.0, 0.0, 0.0]  # Normal vector
        vec2 = [0.0, 0.0, 0.0]  # Zero vector

        # Act
        similarity = memory_backend._calculate_cosine_similarity(vec1, vec2)

        # Assert
        assert similarity == 0.0
