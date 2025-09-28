"""
Tests for RedisVL cache backend implementation.

Following CLAUDE.md: Test behavior, not implementation. One assertion per test when possible.
Focuses on interface compliance and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.infrastructure.cache.backends.redisvl import RedisVLBackend
from app.infrastructure.cache.types import CacheEntry
from core.config import Config


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.hset = AsyncMock(return_value=True)
    client.expire = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.keys = AsyncMock(return_value=[])
    client.hgetall = AsyncMock(return_value={})
    return client


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = MagicMock(spec=Config)
    config.CACHE_REDIS_INDEX_NAME = "test_cache_index"
    config.CACHE_REDIS_KEY_PREFIX = "test_cache:"
    config.CACHE_DEFAULT_TTL = 3600
    config.CACHE_VECTOR_DIMS = 1536
    config.CACHE_VECTOR_ALGORITHM = "HNSW"
    config.CACHE_VECTOR_DISTANCE_METRIC = "COSINE"
    return config


@pytest.fixture
def sample_cache_entry():
    """Sample cache entry for testing"""
    return CacheEntry(
        key="test_key",
        response="Test response",
        embedding=[0.1] * 1536,  # 1536-dimensional embedding
        metadata={"model": "gpt-4", "temperature": 0.7},
        ttl_seconds=3600,
    )


@pytest.fixture
def mock_search_index():
    """Mock RedisVL SearchIndex"""
    index = AsyncMock()
    index.create = AsyncMock()
    index.query = AsyncMock(return_value=[])
    return index


class TestRedisVLBackendInitialization:
    """Test RedisVL backend initialization"""

    def test_initialization_success(self, mock_redis_client, mock_config):
        """Test successful backend initialization"""
        backend = RedisVLBackend(mock_redis_client, mock_config)

        assert backend._redis == mock_redis_client
        assert backend._config == mock_config
        assert backend._index_name == "test_cache_index"
        assert backend._key_prefix == "test_cache:"
        assert backend._vector_dims == 1536

    def test_initialization_uses_config_values(self, mock_redis_client, mock_config):
        """Test that initialization uses configuration values"""
        mock_config.CACHE_VECTOR_DIMS = 768
        mock_config.CACHE_VECTOR_ALGORITHM = "FLAT"
        mock_config.CACHE_VECTOR_DISTANCE_METRIC = "L2"

        backend = RedisVLBackend(mock_redis_client, mock_config)

        assert backend._vector_dims == 768
        assert backend._vector_algorithm == "FLAT"
        assert backend._distance_metric == "L2"


class TestRedisVLBackendStorage:
    """Test RedisVL backend storage operations"""

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_store_entry_success(
        self,
        mock_index_class,
        mock_redis_client,
        mock_config,
        sample_cache_entry,
        mock_search_index,
    ):
        """Test successful entry storage"""
        mock_index_class.return_value = mock_search_index
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.store_entry("test_key", sample_cache_entry)

        assert result is True
        mock_redis_client.hset.assert_called_once()
        mock_redis_client.expire.assert_called_once_with("test_cache:test_key", 3600)

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_store_entry_without_ttl(
        self, mock_index_class, mock_redis_client, mock_config, mock_search_index
    ):
        """Test storing entry without TTL uses default"""
        mock_index_class.return_value = mock_search_index
        backend = RedisVLBackend(mock_redis_client, mock_config)

        entry = CacheEntry(
            key="test_key",
            response="Test response",
            embedding=[0.1] * 1536,
            metadata={},
            ttl_seconds=None,
        )

        result = await backend.store_entry("test_key", entry)

        assert result is True
        # Should not call expire when TTL is None but uses default in data
        mock_redis_client.expire.assert_not_called()

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_store_entry_redis_error(
        self,
        mock_index_class,
        mock_redis_client,
        mock_config,
        sample_cache_entry,
        mock_search_index,
    ):
        """Test storage error handling"""
        mock_index_class.return_value = mock_search_index
        mock_redis_client.hset.side_effect = Exception("Redis error")
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.store_entry("test_key", sample_cache_entry)

        assert result is False

    async def test_store_entry_no_index(self, mock_redis_client, mock_config, sample_cache_entry):
        """Test storage fails when index is not available"""
        backend = RedisVLBackend(mock_redis_client, mock_config)
        # Don't mock the index creation, let it fail

        with patch("app.infrastructure.cache.backends.redisvl.SearchIndex") as mock_index_class:
            mock_index_class.side_effect = Exception("Index creation failed")

            result = await backend.store_entry("test_key", sample_cache_entry)

            assert result is False


class TestRedisVLBackendSearch:
    """Test RedisVL backend search operations"""

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    @patch("app.infrastructure.cache.backends.redisvl.VectorQuery")
    async def test_search_similar_success(
        self, mock_query_class, mock_index_class, mock_redis_client, mock_config, mock_search_index
    ):
        """Test successful similarity search"""
        # Setup mock query results
        mock_query_results = [
            {
                "key": "test_key",
                "response": "Test response",
                "metadata": '{"model": "gpt-4"}',
                "ttl_seconds": "3600",
                "created_at": "1234567890",
                "vector_score": "0.1",  # Distance of 0.1 = similarity of 0.9
            }
        ]
        mock_search_index.query.return_value = mock_query_results
        mock_index_class.return_value = mock_search_index

        backend = RedisVLBackend(mock_redis_client, mock_config)
        embedding = [0.1] * 1536

        results = await backend.search_similar(embedding, threshold=0.8, limit=10)

        assert len(results) == 1
        entry, similarity = results[0]
        assert entry.key == "test_key"
        assert entry.response == "Test response"
        assert similarity == 0.9  # 1.0 - 0.1 distance

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_search_similar_below_threshold(
        self, mock_index_class, mock_redis_client, mock_config, mock_search_index
    ):
        """Test search filters results below threshold"""
        mock_query_results = [
            {
                "key": "test_key",
                "response": "Test response",
                "metadata": "{}",
                "ttl_seconds": "3600",
                "created_at": "1234567890",
                "vector_score": "0.5",  # Distance of 0.5 = similarity of 0.5
            }
        ]
        mock_search_index.query.return_value = mock_query_results
        mock_index_class.return_value = mock_search_index

        backend = RedisVLBackend(mock_redis_client, mock_config)
        embedding = [0.1] * 1536

        results = await backend.search_similar(embedding, threshold=0.8, limit=10)

        assert len(results) == 0  # Below threshold

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_search_similar_no_index(self, mock_index_class, mock_redis_client, mock_config):
        """Test search fails gracefully when index not available"""
        mock_index_class.side_effect = Exception("Index error")
        backend = RedisVLBackend(mock_redis_client, mock_config)

        results = await backend.search_similar([0.1] * 1536, threshold=0.8)

        assert results == []

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_search_similar_redis_error(
        self, mock_index_class, mock_redis_client, mock_config, mock_search_index
    ):
        """Test search error handling"""
        mock_search_index.query.side_effect = Exception("Search error")
        mock_index_class.return_value = mock_search_index
        backend = RedisVLBackend(mock_redis_client, mock_config)

        results = await backend.search_similar([0.1] * 1536, threshold=0.8)

        assert results == []


class TestRedisVLBackendInvalidation:
    """Test RedisVL backend invalidation operations"""

    async def test_invalidate_success(self, mock_redis_client, mock_config):
        """Test successful entry invalidation"""
        mock_redis_client.delete.return_value = 1
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.invalidate("test_key")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_cache:test_key")

    async def test_invalidate_key_not_found(self, mock_redis_client, mock_config):
        """Test invalidation when key doesn't exist"""
        mock_redis_client.delete.return_value = 0
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.invalidate("nonexistent_key")

        assert result is False

    async def test_invalidate_redis_error(self, mock_redis_client, mock_config):
        """Test invalidation error handling"""
        mock_redis_client.delete.side_effect = Exception("Redis error")
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.invalidate("test_key")

        assert result is False


class TestRedisVLBackendClearAll:
    """Test RedisVL backend clear all operations"""

    async def test_clear_all_success(self, mock_redis_client, mock_config):
        """Test successful clear all operation"""
        mock_redis_client.keys.return_value = ["test_cache:key1", "test_cache:key2"]
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.clear_all()

        assert result is True
        mock_redis_client.keys.assert_called_once_with("test_cache:*")
        mock_redis_client.delete.assert_called_once_with("test_cache:key1", "test_cache:key2")

    async def test_clear_all_no_keys(self, mock_redis_client, mock_config):
        """Test clear all when no keys exist"""
        mock_redis_client.keys.return_value = []
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.clear_all()

        assert result is True
        mock_redis_client.delete.assert_not_called()

    async def test_clear_all_redis_error(self, mock_redis_client, mock_config):
        """Test clear all error handling"""
        mock_redis_client.keys.side_effect = Exception("Redis error")
        backend = RedisVLBackend(mock_redis_client, mock_config)

        result = await backend.clear_all()

        assert result is False


class TestRedisVLBackendHealthCheck:
    """Test RedisVL backend health check operations"""

    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_health_check_success(
        self, mock_index_class, mock_redis_client, mock_config, mock_search_index
    ):
        """Test successful health check"""
        mock_redis_client.keys.return_value = ["test_cache:key1", "test_cache:key2"]
        mock_index_class.return_value = mock_search_index
        backend = RedisVLBackend(mock_redis_client, mock_config)

        health = await backend.health_check()

        assert health["storage_healthy"] is True
        assert health["entry_count"] == 2
        assert health["backend_type"] == "redisvl"
        assert health["index_healthy"] is True
        assert health["index_name"] == "test_cache_index"

    async def test_health_check_redis_error(self, mock_redis_client, mock_config):
        """Test health check with Redis connection error"""
        mock_redis_client.ping.side_effect = Exception("Connection error")
        backend = RedisVLBackend(mock_redis_client, mock_config)

        health = await backend.health_check()

        assert health["storage_healthy"] is False
        assert health["entry_count"] == 0
        assert health["backend_type"] == "redisvl"
        assert "error" in health


class TestRedisVLBackendCleanup:
    """Test RedisVL backend cleanup operations"""

    async def test_cleanup_expired_success(self, mock_redis_client, mock_config):
        """Test successful cleanup of expired entries"""
        # Mock keys and their data
        mock_redis_client.keys.return_value = ["test_cache:key1", "test_cache:key2"]

        # Mock expired entry data
        expired_data = {
            "created_at": "1234567000",  # Old timestamp
            "ttl_seconds": "3600",
        }
        valid_data = {
            "created_at": str(int(1234567890 + 3700)),  # Recent timestamp
            "ttl_seconds": "3600",
        }

        mock_redis_client.hgetall.side_effect = [expired_data, valid_data]
        backend = RedisVLBackend(mock_redis_client, mock_config)

        with patch("time.time", return_value=1234567890 + 7200):  # 2 hours later
            cleaned_count = await backend.cleanup_expired()

        assert cleaned_count == 1
        # Should delete the expired key
        mock_redis_client.delete.assert_called_with("test_cache:key1")

    async def test_cleanup_expired_no_expired_entries(self, mock_redis_client, mock_config):
        """Test cleanup when no entries are expired"""
        mock_redis_client.keys.return_value = ["test_cache:key1"]

        # Mock recent entry data
        recent_data = {"created_at": "1234567890", "ttl_seconds": "3600"}
        mock_redis_client.hgetall.return_value = recent_data
        backend = RedisVLBackend(mock_redis_client, mock_config)

        with patch("time.time", return_value=1234567890 + 1800):  # 30 minutes later
            cleaned_count = await backend.cleanup_expired()

        assert cleaned_count == 0
        mock_redis_client.delete.assert_not_called()

    async def test_cleanup_expired_redis_error(self, mock_redis_client, mock_config):
        """Test cleanup error handling"""
        mock_redis_client.keys.side_effect = Exception("Redis error")
        backend = RedisVLBackend(mock_redis_client, mock_config)

        cleaned_count = await backend.cleanup_expired()

        assert cleaned_count == 0


class TestRedisVLBackendIndexManagement:
    """Test RedisVL backend index management"""

    @patch("app.infrastructure.cache.backends.redisvl.IndexSchema")
    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_ensure_index_creation_success(
        self, mock_index_class, mock_schema_class, mock_redis_client, mock_config
    ):
        """Test successful index creation"""
        mock_schema = MagicMock()
        mock_schema_class.from_dict.return_value = mock_schema

        mock_index = AsyncMock()
        mock_index.create = AsyncMock()
        mock_index_class.return_value = mock_index

        backend = RedisVLBackend(mock_redis_client, mock_config)

        # Trigger index creation
        await backend._ensure_index()

        assert backend._index == mock_index
        mock_index.create.assert_called_once_with(overwrite=False)

    @patch("app.infrastructure.cache.backends.redisvl.IndexSchema")
    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_ensure_index_already_exists(
        self, mock_index_class, mock_schema_class, mock_redis_client, mock_config
    ):
        """Test index creation when index already exists"""
        mock_schema = MagicMock()
        mock_schema_class.from_dict.return_value = mock_schema

        mock_index = AsyncMock()
        mock_index.create.side_effect = Exception("Index already exists")
        mock_index_class.return_value = mock_index

        backend = RedisVLBackend(mock_redis_client, mock_config)

        # Should not raise exception
        await backend._ensure_index()

        assert backend._index == mock_index

    @patch("app.infrastructure.cache.backends.redisvl.IndexSchema")
    @patch("app.infrastructure.cache.backends.redisvl.SearchIndex")
    async def test_ensure_index_creation_failure(
        self, mock_index_class, mock_schema_class, mock_redis_client, mock_config
    ):
        """Test index creation failure"""
        mock_schema_class.from_dict.side_effect = Exception("Schema error")

        backend = RedisVLBackend(mock_redis_client, mock_config)

        with pytest.raises(Exception):
            await backend._ensure_index()

        assert backend._index is None
