"""Integration tests for messages domain with the event system"""

from unittest.mock import AsyncMock

import pytest
from app.domains.communication.messages.publisher import MessageEventPublisher
from app.shared.events.broker import broker


class TestMessagesDomainIntegration:
    """Test integration of messages domain with the event system"""

    @pytest.mark.asyncio
    async def test_messages_publisher_integration_with_broker(self):
        """Test that messages publisher integrates properly with the broker"""
        # Create publisher with actual broker instance
        publisher = MessageEventPublisher(broker=broker)

        # Mock the broker's publish method to capture calls
        original_publish = broker.publish
        broker.publish = AsyncMock()

        try:
            # Test publishing a message event
            session_id = "integration-test-session"
            message_data = {
                "content": "Integration test message",
                "user_id": "test-user",
                "chat_id": "test-chat",
            }

            await publisher.message_received(session_id, message_data)

            # Verify broker.publish was called
            broker.publish.assert_called_once()
            call_args = broker.publish.call_args

            # Check the published data structure
            published_data = call_args[0][0]
            channel = call_args[1]["channel"]

            assert channel == "messages.message_received"
            assert published_data["entity_id"] == session_id
            assert published_data["event_type"] == "message_received"
            assert published_data["data"] == message_data

        finally:
            # Restore original publish method
            broker.publish = original_publish

    def test_messages_domain_prefix_consistency(self):
        """Test that messages domain maintains consistent prefix"""
        publisher = MessageEventPublisher(broker=AsyncMock())

        # Test domain prefix
        assert publisher.get_domain_prefix() == "messages"

        # Test channel building
        assert publisher._build_channel("message_received") == "messages.message_received"
        assert publisher._build_channel("message_sent") == "messages.message_sent"

    def test_messages_handlers_and_registry_exist_and_are_callable(self):
        """Test that message handlers and registry exist and can be imported"""
        from app.domains.communication.messages.handlers import (
            handle_message_received,
            handle_message_sent,
        )
        from app.domains.communication.messages.subscribers import MESSAGE_EVENTS

        # Verify handlers are callable
        assert callable(handle_message_received)
        assert callable(handle_message_sent)

        # Verify registry is configured properly
        assert MESSAGE_EVENTS.domain_name == "messages"
        assert len(MESSAGE_EVENTS.event_handlers) == 2
        assert "message_received" in MESSAGE_EVENTS.event_handlers
        assert "message_sent" in MESSAGE_EVENTS.event_handlers

    def test_no_import_errors_with_messages_domain(self):
        """Test that importing messages domain doesn't cause errors"""
        # These imports should not raise any exceptions
        from app.domains.communication.messages import events, handlers, publisher, subscribers

        # Verify key classes are available
        assert hasattr(events, "MessageEvent")
        assert hasattr(events, "MessageEventPayload")
        assert hasattr(publisher, "MessageEventPublisher")
        assert hasattr(subscribers, "MESSAGE_EVENTS")

    def test_messages_domain_types_are_compatible(self):
        """Test that messages domain types are compatible with base types"""
        from app.domains.communication.messages.events import MessageEvent
        from app.domains.communication.messages.publisher import MessageEventPublisher
        from app.shared.events.base import BaseEvent, BaseEventPublisher

        # Test inheritance
        assert issubclass(MessageEvent, BaseEvent)
        assert issubclass(MessageEventPublisher, BaseEventPublisher)

        # Test type compatibility
        event = MessageEvent.message_received("test-session", {"test": "data"})
        assert isinstance(event, BaseEvent)

        publisher = MessageEventPublisher(broker=AsyncMock())
        assert isinstance(publisher, BaseEventPublisher)
