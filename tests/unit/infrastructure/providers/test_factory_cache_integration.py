"""
Tests for cache integration in provider factory.

Following CLAUDE.md: Test integration points and configuration handling.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.infrastructure.cache import SemanticCacheService
from app.infrastructure.cache.middleware.cached_provider import CachedRuntimeAgent
from app.infrastructure.providers.base import RuntimeAgent
from app.infrastructure.providers.factory import wrap_runtime_agents_with_cache
from core.config import Config


class MockRuntimeAgent(RuntimeAgent):
    """Mock runtime agent for testing."""

    def __init__(self, agent_id: str = "test-agent"):
        self._id = agent_id

    async def arun(self, message: str) -> str:
        return f"Response from {self._id}: {message}"

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return f"Agent {self._id}"


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = Mock(spec=Config)
    config.CACHE_AI_PROVIDERS_ENABLED = True
    config.CACHE_ENABLED = True
    return config


@pytest.fixture
def mock_config_disabled():
    """Create a mock config with cache disabled."""
    config = Mock(spec=Config)
    config.CACHE_AI_PROVIDERS_ENABLED = False
    config.CACHE_ENABLED = True
    return config


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    return Mock(spec=SemanticCacheService)


@pytest.fixture
def sample_agents():
    """Create sample runtime agents."""
    return [
        MockRuntimeAgent("agent-1"),
        MockRuntimeAgent("agent-2"),
        MockRuntimeAgent("agent-3"),
    ]


class TestCacheIntegration:
    """Test suite for cache integration factory functions."""

    def test_wrap_runtime_agents_with_cache_enabled(
        self, sample_agents, mock_cache_service, mock_config
    ):
        """Test wrapping agents with cache when enabled."""
        wrapped_agents = wrap_runtime_agents_with_cache(
            runtime_agents=sample_agents,
            cache_service=mock_cache_service,
            config=mock_config,
        )

        # Verify all agents were wrapped
        assert len(wrapped_agents) == len(sample_agents)

        # Verify all wrapped agents are CachedRuntimeAgent instances
        for wrapped_agent in wrapped_agents:
            assert isinstance(wrapped_agent, CachedRuntimeAgent)
            assert wrapped_agent.is_cache_enabled() is True

        # Verify original agents are preserved
        for i, wrapped_agent in enumerate(wrapped_agents):
            original_agent = wrapped_agent.get_wrapped_agent()
            assert original_agent == sample_agents[i]
            assert wrapped_agent.id == sample_agents[i].id
            assert wrapped_agent.name == sample_agents[i].name

    def test_wrap_runtime_agents_cache_disabled_via_provider_flag(
        self, sample_agents, mock_cache_service, mock_config_disabled
    ):
        """Test that cache disabled via CACHE_AI_PROVIDERS_ENABLED returns original agents."""
        wrapped_agents = wrap_runtime_agents_with_cache(
            runtime_agents=sample_agents,
            cache_service=mock_cache_service,
            config=mock_config_disabled,
        )

        # Verify original agents returned unchanged
        assert wrapped_agents == sample_agents
        assert len(wrapped_agents) == len(sample_agents)

        # Verify none are wrapped
        for agent in wrapped_agents:
            assert not isinstance(agent, CachedRuntimeAgent)

    def test_wrap_runtime_agents_cache_globally_disabled(self, sample_agents, mock_cache_service):
        """Test that globally disabled cache returns original agents."""
        config = Mock(spec=Config)
        config.CACHE_AI_PROVIDERS_ENABLED = True
        config.CACHE_ENABLED = False  # Global cache disabled

        wrapped_agents = wrap_runtime_agents_with_cache(
            runtime_agents=sample_agents,
            cache_service=mock_cache_service,
            config=config,
        )

        # Verify original agents returned unchanged
        assert wrapped_agents == sample_agents

    def test_wrap_runtime_agents_empty_list(self, mock_cache_service, mock_config):
        """Test wrapping empty agent list."""
        wrapped_agents = wrap_runtime_agents_with_cache(
            runtime_agents=[],
            cache_service=mock_cache_service,
            config=mock_config,
        )

        assert wrapped_agents == []

    def test_wrap_runtime_agents_error_handling(
        self, sample_agents, mock_cache_service, mock_config
    ):
        """Test that wrapping errors fallback to original agents."""
        import builtins
        from unittest.mock import patch

        # Store original import to restore it
        original_import = builtins.__import__

        def selective_failing_import(name, *args, **kwargs):
            if name == "app.infrastructure.cache.middleware.cached_provider":
                raise ImportError("Simulated cache module import failure")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=selective_failing_import):
            wrapped_agents = wrap_runtime_agents_with_cache(
                runtime_agents=sample_agents,
                cache_service=mock_cache_service,
                config=mock_config,
            )

            # Should return original agents on import error
            assert wrapped_agents == sample_agents

    @pytest.mark.asyncio
    async def test_wrapped_agents_preserve_functionality(
        self, sample_agents, mock_cache_service, mock_config
    ):
        """Test that wrapped agents preserve original functionality."""
        from app.infrastructure.cache.types import CacheResult, CacheSearchResult

        # Setup cache miss so agents are called
        mock_cache_service.get_cached_response = AsyncMock(
            return_value=CacheSearchResult(result=CacheResult.MISS)
        )
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        wrapped_agents = wrap_runtime_agents_with_cache(
            runtime_agents=sample_agents,
            cache_service=mock_cache_service,
            config=mock_config,
        )

        # Test each wrapped agent works
        for i, wrapped_agent in enumerate(wrapped_agents):
            response = await wrapped_agent.arun("test message")
            expected_response = f"Response from agent-{i + 1}: test message"
            assert response == expected_response

            # Verify properties are preserved
            assert wrapped_agent.id == f"agent-{i + 1}"
            assert wrapped_agent.name == f"Agent agent-{i + 1}"

    def test_wrap_runtime_agents_preserves_order(self, mock_cache_service, mock_config):
        """Test that agent order is preserved after wrapping."""
        agents = [MockRuntimeAgent(f"agent-{i}") for i in range(10)]

        wrapped_agents = wrap_runtime_agents_with_cache(
            runtime_agents=agents,
            cache_service=mock_cache_service,
            config=mock_config,
        )

        # Verify order is preserved
        for i, wrapped_agent in enumerate(wrapped_agents):
            assert wrapped_agent.id == f"agent-{i}"
