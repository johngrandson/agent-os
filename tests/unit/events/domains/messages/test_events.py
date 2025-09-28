"""Test message events"""

import pytest
from app.events.domains.messages.events import MessageEvent


class TestMessageEvent:
    """Test MessageEvent class functionality"""

    def test_message_received_event_creation(self) -> None:
        """Test creating a message received event"""
        session_id = "session_123"
        message_data = {
            "content": "Hello world",
            "sender": "user_456",
            "timestamp": "2023-01-01T10:00:00Z",
        }

        event = MessageEvent.message_received(session_id, message_data)

        assert event.entity_id == session_id
        assert event.event_type == "message_received"
        assert event.data == message_data

    def test_message_sent_event_creation(self) -> None:
        """Test creating a message sent event"""
        session_id = "session_789"
        message_data = {
            "content": "Hello back!",
            "recipient": "user_456",
            "timestamp": "2023-01-01T10:01:00Z",
        }

        event = MessageEvent.message_sent(session_id, message_data)

        assert event.entity_id == session_id
        assert event.event_type == "message_sent"
        assert event.data == message_data

    def test_message_event_with_empty_data(self) -> None:
        """Test creating message event with empty data"""
        session_id = "session_empty"
        empty_data = {}

        event = MessageEvent.message_received(session_id, empty_data)

        assert event.entity_id == session_id
        assert event.event_type == "message_received"
        assert event.data == empty_data

    def test_message_event_with_complex_data(self) -> None:
        """Test creating message event with complex nested data"""
        session_id = "session_complex"
        complex_data = {
            "message": {
                "text": "Complex message",
                "attachments": [
                    {"type": "image", "url": "https://example.com/image.jpg"},
                    {"type": "file", "name": "document.pdf"},
                ],
            },
            "metadata": {"channel": "whatsapp", "priority": "high"},
        }

        event = MessageEvent.message_received(session_id, complex_data)

        assert event.entity_id == session_id
        assert event.event_type == "message_received"
        assert event.data == complex_data
        assert event.data["message"]["text"] == "Complex message"
        assert len(event.data["message"]["attachments"]) == 2
