"""Test basic structure for messages domain"""

import pytest
from app.events.domains.messages.events import MessageEvent, MessageEventPayload
from app.events.domains.messages.publisher import MessageEventPublisher


class TestMessageStructure:
    """Test basic structure is working correctly"""

    def test_can_import_message_event(self) -> None:
        """Test that MessageEvent can be imported"""
        assert MessageEvent is not None

    def test_can_import_message_publisher(self) -> None:
        """Test that MessageEventPublisher can be imported"""
        assert MessageEventPublisher is not None

    def test_can_import_message_payload(self) -> None:
        """Test that MessageEventPayload can be imported"""
        assert MessageEventPayload is not None

    def test_message_event_inheritance(self) -> None:
        """Test that MessageEvent properly inherits from BaseEvent"""
        from app.events.core.base import BaseEvent

        assert issubclass(MessageEvent, BaseEvent)

    def test_message_publisher_inheritance(self) -> None:
        """Test that MessageEventPublisher properly inherits from BaseEventPublisher"""
        from app.events.core.base import BaseEventPublisher

        assert issubclass(MessageEventPublisher, BaseEventPublisher)

    def test_publisher_domain_prefix(self) -> None:
        """Test that publisher returns correct domain prefix"""
        # Create a mock broker
        mock_broker = None  # Publisher doesn't use broker in get_domain_prefix
        publisher = MessageEventPublisher(mock_broker)

        assert publisher.get_domain_prefix() == "messages"
