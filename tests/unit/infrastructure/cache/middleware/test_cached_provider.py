"""
Tests for cached runtime agent wrapper.

Following CLAUDE.md: Simple test cases, boring patterns, comprehensive coverage.
"""

from unittest.mock import AsyncMock, Mock, call

import pytest
from app.infrastructure.cache import (
    CacheEntry,
    CacheResult,
    CacheSearchResult,
    SemanticCacheService,
)
from app.infrastructure.cache.middleware.cached_provider import CachedRuntimeAgent
from app.infrastructure.providers.base import RuntimeAgent


class MockRuntimeAgent(RuntimeAgent):
    """Mock runtime agent for testing."""

    def __init__(self, agent_id: str = "test-agent", agent_name: str = "Test Agent"):
        self._id = agent_id
        self._name = agent_name

    async def arun(self, message: str) -> str:
        return f"Response to: {message}"

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


@pytest.fixture
def mock_runtime_agent():
    """Create a mock runtime agent."""
    return MockRuntimeAgent()


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    return Mock(spec=SemanticCacheService)


@pytest.fixture
def cached_agent(mock_runtime_agent, mock_cache_service):
    """Create a cached runtime agent."""
    return CachedRuntimeAgent(
        runtime_agent=mock_runtime_agent,
        cache_service=mock_cache_service,
        enable_cache=True,
    )


class TestCachedRuntimeAgent:
    """Test suite for CachedRuntimeAgent."""

    def test_initialization(self, mock_runtime_agent, mock_cache_service):
        """Test proper initialization of cached agent."""
        cached_agent = CachedRuntimeAgent(
            runtime_agent=mock_runtime_agent,
            cache_service=mock_cache_service,
            enable_cache=True,
        )

        assert cached_agent._agent == mock_runtime_agent
        assert cached_agent._cache == mock_cache_service
        assert cached_agent._enable_cache is True

    def test_properties_delegate_to_wrapped_agent(self, cached_agent, mock_runtime_agent):
        """Test that properties are properly delegated."""
        assert cached_agent.id == mock_runtime_agent.id
        assert cached_agent.name == mock_runtime_agent.name

    def test_get_wrapped_agent(self, cached_agent, mock_runtime_agent):
        """Test access to wrapped agent."""
        assert cached_agent.get_wrapped_agent() == mock_runtime_agent

    def test_is_cache_enabled(self, mock_runtime_agent, mock_cache_service):
        """Test cache enabled status."""
        # Test enabled
        cached_agent = CachedRuntimeAgent(
            runtime_agent=mock_runtime_agent,
            cache_service=mock_cache_service,
            enable_cache=True,
        )
        assert cached_agent.is_cache_enabled() is True

        # Test disabled
        cached_agent = CachedRuntimeAgent(
            runtime_agent=mock_runtime_agent,
            cache_service=mock_cache_service,
            enable_cache=False,
        )
        assert cached_agent.is_cache_enabled() is False

    @pytest.mark.asyncio
    async def test_arun_cache_disabled_goes_to_agent(self, mock_runtime_agent, mock_cache_service):
        """Test that disabled cache goes straight to agent."""
        cached_agent = CachedRuntimeAgent(
            runtime_agent=mock_runtime_agent,
            cache_service=mock_cache_service,
            enable_cache=False,
        )

        # Mock the agent's arun method
        mock_runtime_agent.arun = AsyncMock(return_value="Agent response")

        result = await cached_agent.arun("test message")

        # Verify cache was not called
        mock_cache_service.get_cached_response.assert_not_called()
        mock_cache_service.cache_response.assert_not_called()

        # Verify agent was called
        mock_runtime_agent.arun.assert_called_once_with("test message")
        assert result == "Agent response"

    @pytest.mark.asyncio
    async def test_arun_cache_hit_returns_cached_response(self, cached_agent, mock_cache_service):
        """Test cache hit scenario."""
        # Setup cache hit
        cached_entry = CacheEntry(
            key="test-key",
            response="Cached response",
            embedding=[0.1, 0.2, 0.3],
            metadata={"agent_id": "test-agent"},
        )
        cache_result = CacheSearchResult(
            result=CacheResult.HIT,
            entry=cached_entry,
            similarity_score=0.95,
        )
        mock_cache_service.get_cached_response = AsyncMock(return_value=cache_result)

        # Mock agent (should not be called)
        cached_agent._agent.arun = AsyncMock()

        result = await cached_agent.arun("test message")

        # Verify cache was called with correct metadata
        expected_metadata = {"agent_id": "test-agent", "agent_name": "Test Agent"}
        mock_cache_service.get_cached_response.assert_called_once_with(
            "test message", expected_metadata
        )

        # Verify agent was not called
        cached_agent._agent.arun.assert_not_called()

        # Verify cached response was returned
        assert result == "Cached response"

    @pytest.mark.asyncio
    async def test_arun_cache_miss_calls_agent_and_stores(self, cached_agent, mock_cache_service):
        """Test cache miss scenario with storage."""
        # Setup cache miss
        cache_result = CacheSearchResult(result=CacheResult.MISS)
        mock_cache_service.get_cached_response = AsyncMock(return_value=cache_result)
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        # Mock agent response
        cached_agent._agent.arun = AsyncMock(return_value="Fresh agent response")

        result = await cached_agent.arun("test message")

        # Verify cache lookup was performed
        expected_metadata = {"agent_id": "test-agent", "agent_name": "Test Agent"}
        mock_cache_service.get_cached_response.assert_called_once_with(
            "test message", expected_metadata
        )

        # Verify agent was called
        cached_agent._agent.arun.assert_called_once_with("test message")

        # Verify response was cached
        mock_cache_service.cache_response.assert_called_once_with(
            "test message", "Fresh agent response", expected_metadata
        )

        # Verify fresh response was returned
        assert result == "Fresh agent response"

    @pytest.mark.asyncio
    async def test_arun_cache_error_fallback_to_agent(self, cached_agent, mock_cache_service):
        """Test cache error scenario with fallback."""
        # Setup cache lookup error but storage success
        mock_cache_service.get_cached_response = AsyncMock(
            side_effect=Exception("Cache lookup error")
        )
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        # Mock agent response with a longer response to ensure it passes caching policy
        cached_agent._agent.arun = AsyncMock(
            return_value="Agent response after cache lookup issue - this is a longer response"
        )

        result = await cached_agent.arun("test message for cache error scenario")

        # Verify agent was called despite cache error
        cached_agent._agent.arun.assert_called_once_with("test message for cache error scenario")

        # Verify response was still cached (cache storage might work even if lookup failed)
        expected_metadata = {"agent_id": "test-agent", "agent_name": "Test Agent"}
        mock_cache_service.cache_response.assert_called_once_with(
            "test message for cache error scenario",
            "Agent response after cache lookup issue - this is a longer response",
            expected_metadata,
        )

        # Verify agent response was returned
        assert result == "Agent response after cache lookup issue - this is a longer response"

    @pytest.mark.asyncio
    async def test_arun_cache_storage_error_does_not_fail_request(
        self, cached_agent, mock_cache_service
    ):
        """Test that cache storage errors don't fail the request."""
        # Setup cache miss
        cache_result = CacheSearchResult(result=CacheResult.MISS)
        mock_cache_service.get_cached_response = AsyncMock(return_value=cache_result)
        mock_cache_service.cache_response = AsyncMock(side_effect=Exception("Storage error"))

        # Mock agent response
        cached_agent._agent.arun = AsyncMock(return_value="Agent response")

        result = await cached_agent.arun("test message")

        # Verify agent was called
        cached_agent._agent.arun.assert_called_once_with("test message")

        # Verify cache storage was attempted
        expected_metadata = {"agent_id": "test-agent", "agent_name": "Test Agent"}
        mock_cache_service.cache_response.assert_called_once_with(
            "test message", "Agent response", expected_metadata
        )

        # Verify request succeeded despite cache error
        assert result == "Agent response"

    @pytest.mark.asyncio
    async def test_arun_agent_error_bubbles_up(self, cached_agent, mock_cache_service):
        """Test that agent errors are properly bubbled up."""
        # Setup cache miss
        cache_result = CacheSearchResult(result=CacheResult.MISS)
        mock_cache_service.get_cached_response = AsyncMock(return_value=cache_result)

        # Mock agent error
        cached_agent._agent.arun = AsyncMock(side_effect=Exception("Agent failed"))

        with pytest.raises(Exception, match="Agent failed"):
            await cached_agent.arun("test message")

        # Verify cache lookup was performed
        mock_cache_service.get_cached_response.assert_called_once()

        # Verify agent was called
        cached_agent._agent.arun.assert_called_once_with("test message")

        # Verify no caching attempt on agent failure
        mock_cache_service.cache_response.assert_not_called()

    def test_create_cache_metadata(self, cached_agent):
        """Test cache metadata creation."""
        metadata = cached_agent._create_cache_metadata()

        expected = {
            "agent_id": "test-agent",
            "agent_name": "Test Agent",
        }
        assert metadata == expected

    def test_should_cache_response_valid_cases(self, cached_agent):
        """Test response caching policy for valid cases."""
        # Valid case
        assert cached_agent._should_cache_response("Hello world", "This is a good response") is True

        # Valid with longer content
        assert (
            cached_agent._should_cache_response(
                "What is the weather?",
                "The weather today is sunny with a temperature of 75 degrees Fahrenheit.",
            )
            is True
        )

    def test_should_cache_response_invalid_cases(self, cached_agent):
        """Test response caching policy for invalid cases."""
        # Empty response
        assert cached_agent._should_cache_response("Hello", "") is False
        assert cached_agent._should_cache_response("Hello", "   ") is False

        # Short response
        assert cached_agent._should_cache_response("Hello", "Ok") is False

        # Short message
        assert cached_agent._should_cache_response("Hi", "This is a good response") is False

        # Error responses
        assert cached_agent._should_cache_response("Hello", "Error: something went wrong") is False
        assert cached_agent._should_cache_response("Hello", "Failed to process request") is False
        assert (
            cached_agent._should_cache_response("Hello", "Sorry, I encountered an exception")
            is False
        )
        assert (
            cached_agent._should_cache_response("Hello", "Sorry, I can't help with that") is False
        )

    @pytest.mark.asyncio
    async def test_integration_flow_cache_miss_then_hit(
        self, mock_runtime_agent, mock_cache_service
    ):
        """Test full integration flow: miss, then hit."""
        cached_agent = CachedRuntimeAgent(
            runtime_agent=mock_runtime_agent,
            cache_service=mock_cache_service,
            enable_cache=True,
        )

        # Mock agent
        mock_runtime_agent.arun = AsyncMock(return_value="Agent response")

        # First call - cache miss
        cache_miss = CacheSearchResult(result=CacheResult.MISS)
        mock_cache_service.get_cached_response = AsyncMock(return_value=cache_miss)
        mock_cache_service.cache_response = AsyncMock(return_value=True)

        result1 = await cached_agent.arun("test message")

        # Verify first call
        assert result1 == "Agent response"
        mock_runtime_agent.arun.assert_called_once_with("test message")
        mock_cache_service.cache_response.assert_called_once()

        # Reset mocks for second call
        mock_runtime_agent.arun.reset_mock()
        mock_cache_service.cache_response.reset_mock()

        # Second call - cache hit
        cached_entry = CacheEntry(
            key="test-key",
            response="Agent response",
            embedding=[0.1, 0.2],
            metadata={"agent_id": "test-agent"},
        )
        cache_hit = CacheSearchResult(
            result=CacheResult.HIT,
            entry=cached_entry,
            similarity_score=0.90,
        )
        mock_cache_service.get_cached_response = AsyncMock(return_value=cache_hit)

        result2 = await cached_agent.arun("test message")

        # Verify second call used cache
        assert result2 == "Agent response"
        mock_runtime_agent.arun.assert_not_called()  # Agent should not be called
        mock_cache_service.cache_response.assert_not_called()  # No need to cache again
