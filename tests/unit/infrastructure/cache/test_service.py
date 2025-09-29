"""Tests for simplified semantic cache service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.infrastructure.cache.service import SemanticCacheService
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
    config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"
    return config


@pytest.fixture
def cache_service(mock_openai_client, mock_config):
    """Create cache service for testing"""
    return SemanticCacheService(openai_client=mock_openai_client, config=mock_config)


class TestSemanticCacheService:
    """Test semantic cache service behavior."""

    @pytest.mark.asyncio
    async def test_should_return_none_when_cache_is_empty(self, cache_service, mock_openai_client):
        """When cache is empty, should return None for any query"""
        # Arrange
        mock_openai_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3])
        ]

        # Act
        result = await cache_service.get_cached_response("test query")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_should_store_and_retrieve_exact_match(self, cache_service, mock_openai_client):
        """When storing and retrieving exact same query, should return same response"""
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
        assert retrieve_result == response

    @pytest.mark.asyncio
    async def test_should_return_hit_when_query_exceeds_similarity_threshold(
        self, cache_service, mock_openai_client
    ):
        """When query embedding similarity exceeds threshold, should return cached response"""
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
        assert result == response

    @pytest.mark.asyncio
    async def test_should_return_none_when_query_below_similarity_threshold(
        self, cache_service, mock_openai_client
    ):
        """When query embedding similarity is below threshold, should return None"""
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
        assert result is None

    @pytest.mark.asyncio
    async def test_should_return_none_when_cache_is_disabled(self, mock_openai_client):
        """When cache is disabled in configuration, should return None without checking storage"""
        # Arrange - create service with disabled config
        disabled_config = MagicMock(spec=Config)
        disabled_config.CACHE_ENABLED = False
        disabled_config.CACHE_SIMILARITY_THRESHOLD = 0.8
        disabled_config.CACHE_DEFAULT_TTL = 3600
        disabled_config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"

        disabled_service = SemanticCacheService(
            openai_client=mock_openai_client, config=disabled_config
        )

        # Act
        result = await disabled_service.get_cached_response("test query")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_should_not_store_when_cache_is_disabled(self, mock_openai_client):
        """When cache is disabled in configuration, should not store responses"""
        # Arrange - create service with disabled config
        disabled_config = MagicMock(spec=Config)
        disabled_config.CACHE_ENABLED = False
        disabled_config.CACHE_SIMILARITY_THRESHOLD = 0.8
        disabled_config.CACHE_DEFAULT_TTL = 3600
        disabled_config.CACHE_EMBEDDING_MODEL = "text-embedding-3-small"

        disabled_service = SemanticCacheService(
            openai_client=mock_openai_client, config=disabled_config
        )

        # Act
        result = await disabled_service.cache_response("test query", "test response")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_should_not_cache_short_queries(self, cache_service):
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
        cache_service.clear_cache()

        # Assert - All entries should be removed
        result1 = await cache_service.get_cached_response("query1")
        result2 = await cache_service.get_cached_response("query2")
        assert result1 is None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_should_return_stats(self, cache_service):
        """Should return cache statistics"""
        # Act
        stats = cache_service.get_stats()

        # Assert
        assert "enabled" in stats
        assert "entry_count" in stats
        assert "similarity_threshold" in stats
        assert "default_ttl" in stats
        assert stats["enabled"] is True

    @pytest.mark.asyncio
    async def test_should_handle_embedding_generation_error_gracefully(
        self, cache_service, mock_openai_client
    ):
        """When OpenAI embedding generation fails, should return None without raising exception"""
        # Arrange
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")

        # Act
        result = await cache_service.get_cached_response("test query")

        # Assert - Should handle error gracefully
        assert result is None

    def test_should_calculate_perfect_similarity_for_identical_vectors(self, cache_service):
        """When vectors are identical, cosine similarity should be 1.0"""
        # Arrange
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        # Act
        similarity = cache_service._cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - 1.0) < 0.001

    def test_should_calculate_zero_similarity_for_orthogonal_vectors(self, cache_service):
        """When vectors are orthogonal, cosine similarity should be 0.0"""
        # Arrange
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        # Act
        similarity = cache_service._cosine_similarity(vec1, vec2)

        # Assert
        assert abs(similarity - 0.0) < 0.001

    def test_should_handle_zero_magnitude_vectors_in_similarity_calculation(self, cache_service):
        """When one vector has zero magnitude, cosine similarity should return 0.0"""
        # Arrange
        vec1 = [1.0, 0.0, 0.0]  # Normal vector
        vec2 = [0.0, 0.0, 0.0]  # Zero vector

        # Act
        similarity = cache_service._cosine_similarity(vec1, vec2)

        # Assert
        assert similarity == 0.0
