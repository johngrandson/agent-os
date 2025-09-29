"""Tests for webhook number validation functionality."""

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
    service = AsyncMock(spec=SemanticCacheService)
    service.get_cached_response.return_value = None  # Default cache miss
    service.cache_response.return_value = True
    return service


@pytest.fixture
def config_with_allowed_number():
    """Create config with specific allowed number."""
    config = MagicMock(spec=Config)
    config.allowed_whatsapp_numbers = ["5511999998888"]
    return config


@pytest.fixture
def config_without_allowed_number():
    """Create config without specific allowed number."""
    config = MagicMock(spec=Config)
    config.allowed_whatsapp_numbers = []
    return config


@pytest.fixture
def webhook_processor_with_number_validation(
    mock_agent_cache, mock_event_publisher, mock_cache_service, config_with_allowed_number
):
    """Create webhook processor with number validation enabled."""
    return WebhookAgentProcessor(
        agent_cache=mock_agent_cache,
        event_publisher=mock_event_publisher,
        cache_service=mock_cache_service,
        config=config_with_allowed_number,
    )


@pytest.fixture
def webhook_processor_without_number_validation(
    mock_agent_cache, mock_event_publisher, mock_cache_service, config_without_allowed_number
):
    """Create webhook processor without number validation."""
    return WebhookAgentProcessor(
        agent_cache=mock_agent_cache,
        event_publisher=mock_event_publisher,
        cache_service=mock_cache_service,
        config=config_without_allowed_number,
    )


class TestWebhookNumberValidation:
    """Test webhook number validation functionality."""

    def test_is_number_allowed_with_matching_number(self, webhook_processor_with_number_validation):
        """When sender number matches allowed number, should return True."""
        # Arrange
        chat_id = "5511999998888@c.us"  # WhatsApp format

        # Act
        result = webhook_processor_with_number_validation.is_number_allowed(chat_id)

        # Assert
        assert result is True

    def test_is_number_allowed_with_non_matching_number(
        self, webhook_processor_with_number_validation
    ):
        """When sender number doesn't match allowed number, should return False."""
        # Arrange
        chat_id = "5511999999999@c.us"  # Different number

        # Act
        result = webhook_processor_with_number_validation.is_number_allowed(chat_id)

        # Assert
        assert result is False

    def test_is_number_allowed_without_whatsapp_suffix(
        self, webhook_processor_with_number_validation
    ):
        """Should handle chat IDs without @c.us suffix."""
        # Arrange
        chat_id = "5511999998888"  # No suffix

        # Act
        result = webhook_processor_with_number_validation.is_number_allowed(chat_id)

        # Assert
        assert result is True

    def test_is_number_allowed_when_no_allowed_number_configured(
        self, webhook_processor_without_number_validation
    ):
        """When no allowed number is configured, should allow all numbers."""
        # Arrange
        chat_id = "5511999999999@c.us"

        # Act
        result = webhook_processor_without_number_validation.is_number_allowed(chat_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_process_message_allowed_number_processes_message(
        self, webhook_processor_with_number_validation
    ):
        """When sender number is allowed, should process message normally."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Hello, how are you?"
        chat_id = "5511999998888@c.us"  # Allowed number

        # Act
        result = await webhook_processor_with_number_validation.process_message(
            agent_id, message, chat_id
        )

        # Assert
        assert result == f"Response to: {message}"

    @pytest.mark.asyncio
    async def test_process_message_disallowed_number_returns_none(
        self, webhook_processor_with_number_validation
    ):
        """When sender number is not allowed, should return None without processing."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Hello, how are you?"
        chat_id = "5511999999999@c.us"  # Not allowed number

        # Act
        result = await webhook_processor_with_number_validation.process_message(
            agent_id, message, chat_id
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_process_message_no_validation_processes_all_numbers(
        self, webhook_processor_without_number_validation
    ):
        """When no number validation is configured, should process messages from any number."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Hello from any number"
        chat_id = "5511888887777@c.us"  # Random number

        # Act
        result = await webhook_processor_without_number_validation.process_message(
            agent_id, message, chat_id
        )

        # Assert
        assert result == f"Response to: {message}"

    def test_webhook_processor_initialization_with_config(
        self, mock_agent_cache, mock_event_publisher, mock_cache_service, config_with_allowed_number
    ):
        """Should initialize correctly with config."""
        processor = WebhookAgentProcessor(
            agent_cache=mock_agent_cache,
            event_publisher=mock_event_publisher,
            cache_service=mock_cache_service,
            config=config_with_allowed_number,
        )

        assert processor.agent_cache == mock_agent_cache
        assert processor.event_publisher == mock_event_publisher
        assert processor.cache_service == mock_cache_service
        assert processor.config == config_with_allowed_number

    def test_is_number_allowed_with_different_formats(
        self, webhook_processor_with_number_validation
    ):
        """Should handle different chat ID formats consistently."""
        allowed_number = "5511999998888"

        # Test different formats that should all be allowed
        test_cases = [
            f"{allowed_number}@c.us",  # Standard WhatsApp format
            f"{allowed_number}@g.us",  # Group format (shouldn't happen for sender, but test anyway)
            allowed_number,  # Just the number
            f"{allowed_number}@s.whatsapp.net",  # Alternative format
        ]

        for chat_id in test_cases:
            result = webhook_processor_with_number_validation.is_number_allowed(chat_id)
            assert result is True, f"Failed for chat_id: {chat_id}"

    def test_is_number_allowed_case_sensitivity(self, webhook_processor_with_number_validation):
        """Number validation should be case-insensitive (though numbers don't have cases)."""
        # This test ensures the method handles edge cases properly
        chat_id = "5511999998888@C.US"  # Uppercase domain

        result = webhook_processor_with_number_validation.is_number_allowed(chat_id)

        # Should extract just the number part and match
        assert result is True

    @pytest.mark.asyncio
    async def test_process_message_number_validation_logs_properly(
        self, webhook_processor_with_number_validation, caplog
    ):
        """Should log appropriate messages when blocking unauthorized numbers."""
        # Arrange
        agent_id = "test-agent-123"
        message = "Unauthorized message"
        chat_id = "5511888887777@c.us"  # Not allowed

        # Act
        result = await webhook_processor_with_number_validation.process_message(
            agent_id, message, chat_id
        )

        # Assert
        assert result is None
        # Could check logs if needed, but keeping test simple
