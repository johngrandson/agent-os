"""Tests for WebhookAgentProcessor with semantic cache integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.domains.agent_management.agent import Agent
from app.domains.communication.messages.publisher import MessageEventPublisher
from app.domains.communication.webhooks.services.webhook_agent_processor import (
    WebhookAgentProcessor,
)
from app.infrastructure.cache.service import SemanticCacheService
from app.infrastructure.providers.base import RuntimeAgent
from app.initialization import AgentCache
from core.config import Config


class MockRuntimeAgent(RuntimeAgent):
    """Mock runtime agent for testing."""

    def __init__(self, agent_id: str = "test-agent", agent_name: str = "Test Agent"):
        self._id = agent_id
        self._name = agent_name

    async def arun(self, message: str) -> MagicMock:
        """Mock arun that returns a response with content."""
        response = MagicMock()
        response.content = f"Response to: {message}"
        return response

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


@pytest.fixture
def mock_db_agent():
    """Create a mock DB agent."""
    agent = MagicMock(spec=Agent)
    agent.id = "test-agent-123"
    agent.is_active = True
    return agent


@pytest.fixture
def mock_runtime_agent():
    """Create a mock runtime agent."""
    return MockRuntimeAgent("test-agent-123", "Test Agent")


@pytest.fixture
def mock_agent_cache(mock_db_agent, mock_runtime_agent):
    """Create a mock agent cache."""
    cache = MagicMock(spec=AgentCache)
    cache.get_loaded_db_agents.return_value = [mock_db_agent]
    cache.find_agent_by_id.return_value = mock_runtime_agent
    return cache


@pytest.fixture
def mock_event_publisher():
    """Create a mock event publisher."""
    return MagicMock(spec=MessageEventPublisher)


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    return AsyncMock(spec=SemanticCacheService)


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = MagicMock(spec=Config)
    config.WEBHOOK_ALLOWED_NUMBER = None  # No number restriction by default
    return config


@pytest.fixture
def webhook_processor_with_cache(
    mock_agent_cache, mock_event_publisher, mock_cache_service, mock_config
):
    """Create webhook processor with cache."""
    return WebhookAgentProcessor(
        agent_cache=mock_agent_cache,
        event_publisher=mock_event_publisher,
        cache_service=mock_cache_service,
        config=mock_config,
    )


@pytest.fixture
def webhook_processor_without_cache(mock_agent_cache, mock_event_publisher, mock_config):
    """Create webhook processor without cache."""
    return WebhookAgentProcessor(
        agent_cache=mock_agent_cache,
        event_publisher=mock_event_publisher,
        cache_service=None,
        config=mock_config,
    )


class TestWebhookAgentProcessorCache:
    """Test webhook agent processor with cache integration."""

    @pytest.mark.asyncio
    async def test_process_message_cache_hit(
        self, webhook_processor_with_cache, mock_cache_service
    ):
        """When cache has response, should return cached response without calling agent."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Hello, how are you?"
        chat_id = "chat123"
        cached_response = "I'm doing well, thank you!"

        mock_cache_service.get_cached_response.return_value = cached_response

        # Act
        result = await webhook_processor_with_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result == cached_response
        mock_cache_service.get_cached_response.assert_called_once_with(
            f"agent:{agent_id}|message:{message}"
        )
        # Should not call cache_response since we got a cache hit
        mock_cache_service.cache_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_cache_miss_then_cache_response(
        self, webhook_processor_with_cache, mock_cache_service
    ):
        """When cache miss, should call agent and cache the response."""
        # Arrange
        agent_id = "test-agent-123"
        message = "What's the weather like?"
        chat_id = "chat123"

        mock_cache_service.get_cached_response.return_value = None  # Cache miss
        mock_cache_service.cache_response.return_value = True

        # Act
        result = await webhook_processor_with_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result == f"Response to: {message}"
        mock_cache_service.get_cached_response.assert_called_once_with(
            f"agent:{agent_id}|message:{message}"
        )
        mock_cache_service.cache_response.assert_called_once_with(
            f"agent:{agent_id}|message:{message}", f"Response to: {message}"
        )

    @pytest.mark.asyncio
    async def test_process_message_without_cache_service(
        self, webhook_processor_without_cache, mock_agent_cache
    ):
        """When no cache service, should process normally without caching."""
        # Arrange
        agent_id = "test-agent-123"
        message = "How can you help me?"
        chat_id = "chat123"

        # Act
        result = await webhook_processor_without_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result == f"Response to: {message}"

    @pytest.mark.asyncio
    async def test_process_message_cache_lookup_error(
        self, webhook_processor_with_cache, mock_cache_service
    ):
        """When cache lookup fails, should continue with agent processing."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Tell me a joke"
        chat_id = "chat123"

        mock_cache_service.get_cached_response.side_effect = Exception("Cache lookup failed")
        mock_cache_service.cache_response.return_value = True

        # Act
        result = await webhook_processor_with_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result == f"Response to: {message}"
        mock_cache_service.cache_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_cache_storage_error(
        self, webhook_processor_with_cache, mock_cache_service
    ):
        """When cache storage fails, should still return agent response."""
        # Arrange
        agent_id = "test-agent-123"
        message = "What's your name?"
        chat_id = "chat123"

        mock_cache_service.get_cached_response.return_value = None  # Cache miss
        mock_cache_service.cache_response.side_effect = Exception("Cache storage failed")

        # Act
        result = await webhook_processor_with_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result == f"Response to: {message}"
        mock_cache_service.get_cached_response.assert_called_once()
        mock_cache_service.cache_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_invalid_agent(
        self, webhook_processor_with_cache, mock_agent_cache, mock_cache_service
    ):
        """When agent is not valid for webhook, should return None without cache interaction."""
        # Arrange
        agent_id = "invalid-agent"
        message = "Hello"
        chat_id = "chat123"

        mock_agent_cache.get_loaded_db_agents.return_value = []  # No valid agents

        # Act
        result = await webhook_processor_with_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result is None
        mock_cache_service.get_cached_response.assert_not_called()
        mock_cache_service.cache_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_agent_not_found(
        self, webhook_processor_with_cache, mock_agent_cache, mock_cache_service
    ):
        """When agent is not found in cache, should return None without cache interaction."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Hello"
        chat_id = "chat123"

        mock_agent_cache.find_agent_by_id.return_value = None  # Agent not found

        # Act
        result = await webhook_processor_with_cache.process_message(agent_id, message, chat_id)

        # Assert
        assert result is None
        mock_cache_service.get_cached_response.assert_not_called()
        mock_cache_service.cache_response.assert_not_called()

    def test_webhook_processor_initialization_with_cache(
        self, mock_agent_cache, mock_event_publisher, mock_cache_service, mock_config
    ):
        """Should initialize correctly with cache service."""
        processor = WebhookAgentProcessor(
            agent_cache=mock_agent_cache,
            event_publisher=mock_event_publisher,
            cache_service=mock_cache_service,
            config=mock_config,
        )

        assert processor.agent_cache == mock_agent_cache
        assert processor.event_publisher == mock_event_publisher
        assert processor.cache_service == mock_cache_service
        assert processor.config == mock_config

    def test_webhook_processor_initialization_without_cache(
        self, mock_agent_cache, mock_event_publisher, mock_config
    ):
        """Should initialize correctly without cache service."""
        processor = WebhookAgentProcessor(
            agent_cache=mock_agent_cache,
            event_publisher=mock_event_publisher,
            cache_service=None,
            config=mock_config,
        )

        assert processor.agent_cache == mock_agent_cache
        assert processor.event_publisher == mock_event_publisher
        assert processor.cache_service is None
        assert processor.config == mock_config
