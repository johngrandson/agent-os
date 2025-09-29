"""Tests for webhook schemas handling different event types."""

import pytest
from app.domains.communication.webhooks.api.schemas import (
    MessagePayload,
    SessionStatusPayload,
    WebhookData,
)


class TestWebhookSchemas:
    """Test webhook schema parsing for different event types."""

    def test_message_payload_parsing(self):
        """Should parse message payload correctly."""
        data = {
            "from": "5511999998888@c.us",
            "body": "Hello world",
            "type": "chat",
            "sent_by_bot": False,
            "timestamp": 1234567890,
            "id": "msg_123",
        }

        payload = MessagePayload(**data)

        assert payload.chat_id == "5511999998888@c.us"
        assert payload.body == "Hello world"
        assert payload.type == "chat"
        assert payload.sent_by_bot is False
        assert payload.timestamp == 1234567890
        assert payload.id == "msg_123"

    def test_session_status_payload_parsing(self):
        """Should parse session status payload correctly."""
        data = {
            "name": "default",
            "status": "WORKING",
            "statuses": [
                {"status": "STOPPED", "timestamp": 1759111461354},
                {"status": "STARTING", "timestamp": 1759111461364},
                {"status": "WORKING", "timestamp": 1759111469840},
            ],
        }

        payload = SessionStatusPayload(**data)

        assert payload.name == "default"
        assert payload.status == "WORKING"
        assert len(payload.statuses) == 3
        assert payload.statuses[0]["status"] == "STOPPED"

    def test_webhook_data_with_message_event(self):
        """Should handle WebhookData with message event."""
        data = {
            "event": "message",
            "payload": {
                "from": "5511999998888@c.us",
                "body": "Test message",
                "type": "chat",
                "sent_by_bot": False,
            },
            "metadata": {"agent.id": "test-agent-123"},
        }

        webhook = WebhookData(**data)

        assert webhook.event == "message"
        assert webhook.is_message_event() is True
        assert webhook.is_session_status_event() is False
        assert isinstance(webhook.payload, MessagePayload)
        assert webhook.get_chat_id() == "5511999998888@c.us"
        assert webhook.get_message_body() == "Test message"
        assert webhook.get_agent_id() == "test-agent-123"
        assert webhook.is_from_bot() is False

    def test_webhook_data_with_session_status_event(self):
        """Should handle WebhookData with session status event."""
        data = {
            "event": "session.status",
            "payload": {
                "name": "default",
                "status": "WORKING",
                "statuses": [
                    {"status": "STOPPED", "timestamp": 1759111461354},
                    {"status": "STARTING", "timestamp": 1759111461364},
                    {"status": "WORKING", "timestamp": 1759111469840},
                ],
            },
        }

        webhook = WebhookData(**data)

        assert webhook.event == "session.status"
        assert webhook.is_session_status_event() is True
        assert webhook.is_message_event() is False
        assert isinstance(webhook.payload, SessionStatusPayload)
        assert webhook.get_chat_id() is None  # No chat_id for session events
        assert webhook.get_message_body() is None  # No message body for session events
        assert webhook.get_agent_id() is None  # No metadata provided
        assert webhook.is_from_bot() is False  # False for non-message events

    def test_webhook_data_session_status_exactly_like_error_logs(self):
        """Should parse session status data exactly like in the error logs."""
        # This is the exact data from the error logs that was causing 422 errors
        data = {
            "event": "session.status",
            "payload": {
                "name": "default",
                "status": "WORKING",
                "statuses": [
                    {"status": "STOPPED", "timestamp": 1759111461354},
                    {"status": "STARTING", "timestamp": 1759111461364},
                    {"status": "WORKING", "timestamp": 1759111469840},
                ],
            },
        }

        # This should NOT raise a validation error anymore
        webhook = WebhookData(**data)

        assert webhook.event == "session.status"
        assert webhook.is_session_status_event() is True
        assert webhook.payload.name == "default"
        assert webhook.payload.status == "WORKING"
        assert len(webhook.payload.statuses) == 3

    def test_webhook_data_handles_unknown_event_type(self):
        """Should handle unknown event types gracefully."""
        data = {
            "event": "unknown.event",
            "payload": {
                "name": "default",
                "status": "WORKING",
                "statuses": [],
            },
        }

        webhook = WebhookData(**data)

        assert webhook.event == "unknown.event"
        assert webhook.is_message_event() is False
        assert webhook.is_session_status_event() is False

    def test_message_payload_with_alias_from_field(self):
        """Should handle 'from' field alias correctly."""
        data = {
            "from": "5511999998888@c.us",  # This should map to chat_id
            "body": "Test",
        }

        payload = MessagePayload(**data)
        assert payload.chat_id == "5511999998888@c.us"

    def test_webhook_metadata_with_agent_id_alias(self):
        """Should handle agent.id alias correctly."""
        data = {
            "event": "message",
            "payload": {"from": "5511999998888@c.us", "body": "Test"},
            "metadata": {"agent.id": "test-agent-123"},
        }

        webhook = WebhookData(**data)
        assert webhook.get_agent_id() == "test-agent-123"

    def test_optional_fields_in_message_payload(self):
        """Should handle optional fields gracefully."""
        # Minimum required fields
        data = {"from": "5511999998888@c.us", "body": "Test"}

        payload = MessagePayload(**data)

        assert payload.chat_id == "5511999998888@c.us"
        assert payload.body == "Test"
        assert payload.sent_by_bot is False  # Default value
        assert payload.type == "chat"  # Default value
        assert payload.timestamp is None  # Optional field
        assert payload.id is None  # Optional field
