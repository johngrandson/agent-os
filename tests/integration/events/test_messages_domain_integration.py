"""Integration tests for messages domain with the event system"""

from unittest.mock import AsyncMock

import pytest
from app.events.broker import broker
from app.events.core.registry import event_registry
from app.events.domains.messages.publisher import MessageEventPublisher
from app.events.domains.messages.subscribers import message_router


class TestMessagesDomainIntegration:
    """Test integration of messages domain with the event system"""

    def test_messages_router_is_registered_with_event_registry(self):
        """Test that messages router is properly registered"""
        # The subscriber import should have registered the router
        from app.events.domains.messages import subscribers  # noqa: F401

        # Verify the router is registered
        registered_router = event_registry.get_domain_router("messages")
        assert registered_router is message_router

    def test_messages_domain_integrates_with_event_system(self):
        """Test that messages domain integrates properly with the event system"""
        # Import messages domain subscribers
        from app.events.domains.messages import subscribers as message_subscribers  # noqa: F401

        # Verify messages router is registered
        message_router = event_registry.get_domain_router("messages")
        assert message_router is not None

        # Verify messages domain is included in all registered domains
        all_routers = event_registry.get_all_routers()
        assert "messages" in all_routers

    def test_all_registered_domains_include_messages(self):
        """Test that messages domain appears in all registered domains"""
        # Import subscribers to ensure registration
        from app.events.domains.messages import subscribers  # noqa: F401

        all_routers = event_registry.get_all_routers()
        domain_names = list(all_routers.keys())

        assert "messages" in domain_names

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

    def test_messages_handlers_and_subscribers_exist_and_are_callable(self):
        """Test that message handlers and subscribers exist and can be imported"""
        from app.events.domains.messages.handlers import (
            handle_message_received,
            handle_message_sent,
        )
        from app.events.domains.messages.subscribers import (
            message_received_subscriber,
            message_sent_subscriber,
        )

        # Verify handlers are callable
        assert callable(handle_message_received)
        assert callable(handle_message_sent)
        # Verify subscribers are callable
        assert callable(message_received_subscriber)
        assert callable(message_sent_subscriber)

    def test_no_import_errors_with_messages_domain(self):
        """Test that importing messages domain doesn't cause errors"""
        # These imports should not raise any exceptions
        from app.events.domains.messages import events, handlers, publisher, subscribers

        # Verify key classes are available
        assert hasattr(events, "MessageEvent")
        assert hasattr(events, "MessageEventPayload")
        assert hasattr(publisher, "MessageEventPublisher")
        assert hasattr(subscribers, "message_router")

    def test_messages_domain_types_are_compatible(self):
        """Test that messages domain types are compatible with base types"""
        from app.events.core.base import BaseEvent, BaseEventPublisher
        from app.events.domains.messages.events import MessageEvent, MessageEventPayload
        from app.events.domains.messages.publisher import MessageEventPublisher

        # Test inheritance
        assert issubclass(MessageEvent, BaseEvent)
        assert issubclass(MessageEventPublisher, BaseEventPublisher)

        # Test type compatibility
        event = MessageEvent.message_received("test-session", {"test": "data"})
        assert isinstance(event, BaseEvent)

        publisher = MessageEventPublisher(broker=AsyncMock())
        assert isinstance(publisher, BaseEventPublisher)
