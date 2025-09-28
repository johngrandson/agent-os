"""
Tests for cache backend factory.

Following CLAUDE.md: Test behavior, not implementation.
    Focus on factory logic and fallback behavior.
"""

from unittest.mock import MagicMock, patch

import pytest
from app.infrastructure.cache.backends.factory import create_backend
from app.infrastructure.cache.backends.memory import MemoryBackend
from core.config import Config


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = MagicMock()
    client.ping = MagicMock(return_value=True)
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


class TestBackendFactoryMemory:
    """Test backend factory memory backend creation"""

    def test_create_memory_backend(self):
        """Test creating memory backend"""
        backend = create_backend("memory")

        assert isinstance(backend, MemoryBackend)

    def test_create_memory_backend_case_insensitive(self):
        """Test memory backend creation is case insensitive"""
        backend = create_backend("MEMORY")

        assert isinstance(backend, MemoryBackend)

    def test_create_memory_backend_with_whitespace(self):
        """Test memory backend creation handles whitespace"""
        backend = create_backend("  memory  ")

        assert isinstance(backend, MemoryBackend)


class TestBackendFactoryRedisVL:
    """Test backend factory RedisVL backend creation and fallback"""

    @patch("app.infrastructure.cache.backends.redisvl.RedisVLBackend")
    def test_create_redisvl_backend_success(
        self, mock_redisvl_class, mock_redis_client, mock_config
    ):
        """Test successful RedisVL backend creation"""
        mock_backend = MagicMock()
        mock_redisvl_class.return_value = mock_backend

        backend = create_backend("redisvl", redis_client=mock_redis_client, config=mock_config)

        assert backend == mock_backend
        mock_redisvl_class.assert_called_once_with(mock_redis_client, mock_config)

    def test_create_redisvl_backend_no_redis_client(self, mock_config):
        """Test RedisVL backend falls back to memory when no Redis client"""
        backend = create_backend("redisvl", config=mock_config)

        assert isinstance(backend, MemoryBackend)

    def test_create_redisvl_backend_no_config(self, mock_redis_client):
        """Test RedisVL backend falls back to memory when no config"""
        backend = create_backend("redisvl", redis_client=mock_redis_client)

        assert isinstance(backend, MemoryBackend)

    @patch("app.infrastructure.cache.backends.redisvl.RedisVLBackend")
    def test_create_redisvl_backend_connection_failure(
        self, mock_redisvl_class, mock_redis_client, mock_config
    ):
        """Test RedisVL backend falls back to memory on connection failure"""
        mock_redisvl_class.side_effect = Exception("Connection failed")

        backend = create_backend("redisvl", redis_client=mock_redis_client, config=mock_config)

        assert isinstance(backend, MemoryBackend)

    def test_create_redisvl_backend_import_error(self, mock_redis_client, mock_config):
        """Test RedisVL backend falls back to memory when RedisVL import fails"""
        # Import sys to manipulate module cache
        import sys

        # Store original module if it exists
        original_module = sys.modules.get("app.infrastructure.cache.backends.redisvl")

        try:
            # Remove module from cache to force re-import
            if "app.infrastructure.cache.backends.redisvl" in sys.modules:
                del sys.modules["app.infrastructure.cache.backends.redisvl"]

            # Create a mock that raises ImportError when trying to import
            class FailingModule:
                def __getattr__(self, name):
                    raise ImportError("RedisVL not available")

            # Mock the module in sys.modules to raise ImportError
            sys.modules["app.infrastructure.cache.backends.redisvl"] = FailingModule()

            # This should trigger the ImportError and fallback to memory
            backend = create_backend("redisvl", redis_client=mock_redis_client, config=mock_config)

        finally:
            # Always restore the original state
            if original_module is not None:
                sys.modules["app.infrastructure.cache.backends.redisvl"] = original_module
            elif "app.infrastructure.cache.backends.redisvl" in sys.modules:
                del sys.modules["app.infrastructure.cache.backends.redisvl"]

        assert isinstance(backend, MemoryBackend)

    @patch("app.infrastructure.cache.backends.redisvl.RedisVLBackend")
    def test_create_redisvl_backend_case_insensitive(
        self, mock_redisvl_class, mock_redis_client, mock_config
    ):
        """Test RedisVL backend creation is case insensitive"""
        mock_backend = MagicMock()
        mock_redisvl_class.return_value = mock_backend

        backend = create_backend("REDISVL", redis_client=mock_redis_client, config=mock_config)

        assert backend == mock_backend


class TestBackendFactoryErrors:
    """Test backend factory error handling"""

    def test_create_backend_unknown_type(self):
        """Test factory raises error for unknown backend type"""
        with pytest.raises(ValueError) as exc_info:
            create_backend("unknown_backend")

        assert "Unknown backend type: unknown_backend" in str(exc_info.value)
        assert "Supported backends: memory, redisvl" in str(exc_info.value)

    def test_create_backend_empty_string(self):
        """Test factory raises error for empty backend type"""
        with pytest.raises(ValueError) as exc_info:
            create_backend("")

        assert "Unknown backend type:" in str(exc_info.value)

    def test_create_backend_none_type(self):
        """Test factory handles None backend type gracefully"""
        with pytest.raises(AttributeError):
            # This will fail when trying to call .lower().strip() on None
            create_backend(None)


class TestBackendFactoryKwargsHandling:
    """Test backend factory kwargs handling"""

    def test_memory_backend_ignores_extra_kwargs(self):
        """Test memory backend ignores extra kwargs"""
        backend = create_backend(
            "memory", redis_client=MagicMock(), config=MagicMock(), extra_param="ignored"
        )

        assert isinstance(backend, MemoryBackend)

    @patch("app.infrastructure.cache.backends.redisvl.RedisVLBackend")
    def test_redisvl_backend_uses_required_kwargs(
        self, mock_redisvl_class, mock_redis_client, mock_config
    ):
        """Test RedisVL backend uses required kwargs"""
        mock_backend = MagicMock()
        mock_redisvl_class.return_value = mock_backend

        backend = create_backend(
            "redisvl",
            redis_client=mock_redis_client,
            config=mock_config,
            extra_param="ignored",  # Should be ignored
        )

        assert backend == mock_backend
        mock_redisvl_class.assert_called_once_with(mock_redis_client, mock_config)

    def test_redisvl_backend_partial_kwargs(self, mock_redis_client):
        """Test RedisVL backend with partial kwargs falls back to memory"""
        # Only provide redis_client, missing config
        backend = create_backend("redisvl", redis_client=mock_redis_client)

        assert isinstance(backend, MemoryBackend)
