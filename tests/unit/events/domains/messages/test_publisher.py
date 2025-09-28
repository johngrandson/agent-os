"""Test message event publisher"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.domains.communication.messages.events import MessageEvent
from app.domains.communication.messages.publisher import MessageEventPublisher


class TestMessageEventPublisher:
    """Test MessageEventPublisher functionality"""

    def setup_method(self) -> None:
        """Set up test fixtures"""
        self.mock_broker = AsyncMock()
        self.publisher = MessageEventPublisher(self.mock_broker)

    def test_publisher_domain_prefix(self) -> None:
        """Test publisher returns correct domain prefix"""
        assert self.publisher.get_domain_prefix() == "messages"

    def test_build_channel_with_domain_prefix(self) -> None:
        """Test channel building with domain prefix"""
        channel = self.publisher._build_channel("message_received")
        assert channel == "messages.message_received"

    @pytest.mark.asyncio
    async def test_publish_message_received_event(self) -> None:
        """Test publishing message received event"""
        session_id = "session_123"
        message_data = {"content": "Test message", "sender": "user_456"}

        # Mock the publish method to avoid actual broker calls
        self.publisher.publish = AsyncMock()

        await self.publisher.message_received(session_id, message_data)

        # Verify publish was called with correct parameters
        self.publisher.publish.assert_called_once()

        # Get the call arguments
        call_args = self.publisher.publish.call_args
        channel = call_args[0][0]
        event = call_args[0][1]

        assert channel == "messages.message_received"
        assert isinstance(event, MessageEvent)
        assert event.entity_id == session_id
        assert event.event_type == "message_received"
        assert event.data == message_data

    @pytest.mark.asyncio
    async def test_publish_message_sent_event(self) -> None:
        """Test publishing message sent event"""
        session_id = "session_789"
        message_data = {"content": "Response message", "recipient": "user_456"}

        # Mock the publish method to avoid actual broker calls
        self.publisher.publish = AsyncMock()

        await self.publisher.message_sent(session_id, message_data)

        # Verify publish was called with correct parameters
        self.publisher.publish.assert_called_once()

        # Get the call arguments
        call_args = self.publisher.publish.call_args
        channel = call_args[0][0]
        event = call_args[0][1]

        assert channel == "messages.message_sent"
        assert isinstance(event, MessageEvent)
        assert event.entity_id == session_id
        assert event.event_type == "message_sent"
        assert event.data == message_data

    @pytest.mark.asyncio
    async def test_publisher_handles_empty_data(self) -> None:
        """Test publisher can handle empty message data"""
        session_id = "session_empty"
        empty_data = {}

        # Mock the publish method
        self.publisher.publish = AsyncMock()

        await self.publisher.message_received(session_id, empty_data)

        # Verify it was called correctly
        self.publisher.publish.assert_called_once()
        call_args = self.publisher.publish.call_args
        event = call_args[0][1]

        assert event.data == empty_data

    @pytest.mark.asyncio
    async def test_publisher_handles_complex_data(self) -> None:
        """Test publisher can handle complex nested data"""
        session_id = "session_complex"
        complex_data = {
            "message": {"text": "Complex message", "metadata": {"priority": "high"}},
            "attachments": [{"type": "image"}],
        }

        # Mock the publish method
        self.publisher.publish = AsyncMock()

        await self.publisher.message_received(session_id, complex_data)

        # Verify it was called correctly
        self.publisher.publish.assert_called_once()
        call_args = self.publisher.publish.call_args
        event = call_args[0][1]

        assert event.data == complex_data
        assert event.data["message"]["metadata"]["priority"] == "high"
