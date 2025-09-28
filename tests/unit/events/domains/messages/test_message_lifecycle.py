"""Tests for complete message lifecycle scenarios"""

from unittest.mock import AsyncMock

import pytest
from app.domains.communication.messages.events import MessageEvent
from app.domains.communication.messages.publisher import MessageEventPublisher


class TestMessageLifecycle:
    """Test complete message lifecycle scenarios"""

    @pytest.fixture
    def publisher(self):
        """Message publisher with mocked publish method"""
        mock_broker = AsyncMock()
        publisher = MessageEventPublisher(broker=mock_broker)
        publisher.publish = AsyncMock()
        return publisher

    @pytest.mark.asyncio
    async def test_complete_message_received_to_sent_lifecycle(self, publisher):
        """Test complete lifecycle: message received -> message sent"""
        session_id = "lifecycle-session-123"

        # Step 1: Message received
        received_data = {
            "message_content": "User question",
            "user_id": "user-456",
            "chat_id": "chat-789",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        await publisher.message_received(session_id, received_data)

        # Verify message_received event was published
        assert publisher.publish.call_count == 1
        received_call = publisher.publish.call_args_list[0]
        received_channel = received_call[0][0]
        received_event = received_call[0][1]

        assert received_channel == "messages.message_received"
        assert received_event.entity_id == session_id
        assert received_event.event_type == "message_received"
        assert received_event.data == received_data

        # Step 2: Message sent (AI response)
        sent_data = {
            "message_content": "AI response to user question",
            "agent_id": "agent-ai-001",
            "chat_id": "chat-789",
            "timestamp": "2024-01-01T12:01:00Z",
            "delivery_status": "sent",
            "response_to": received_data["message_content"],
        }

        await publisher.message_sent(session_id, sent_data)

        # Verify message_sent event was published
        assert publisher.publish.call_count == 2
        sent_call = publisher.publish.call_args_list[1]
        sent_channel = sent_call[0][0]
        sent_event = sent_call[0][1]

        assert sent_channel == "messages.message_sent"
        assert sent_event.entity_id == session_id
        assert sent_event.event_type == "message_sent"
        assert sent_event.data == sent_data

    @pytest.mark.asyncio
    async def test_multiple_message_types_in_session(self, publisher):
        """Test handling multiple message types within same session"""
        session_id = "multi-message-session"

        # Message 1: User message received
        user_message = {
            "message_content": "First user message",
            "user_id": "user-123",
            "chat_id": "chat-456",
        }
        await publisher.message_received(session_id, user_message)

        # Message 2: AI response sent
        ai_response = {
            "message_content": "AI response to first message",
            "agent_id": "agent-001",
            "chat_id": "chat-456",
            "delivery_status": "sent",
        }
        await publisher.message_sent(session_id, ai_response)

        # Message 3: Follow-up user message received
        followup_message = {
            "message_content": "Follow-up question",
            "user_id": "user-123",
            "chat_id": "chat-456",
        }
        await publisher.message_received(session_id, followup_message)

        # Message 4: Second AI response sent
        second_response = {
            "message_content": "Response to follow-up",
            "agent_id": "agent-001",
            "chat_id": "chat-456",
            "delivery_status": "sent",
        }
        await publisher.message_sent(session_id, second_response)

        # Verify all 4 events were published correctly
        assert publisher.publish.call_count == 4

        # Check that events alternate between received and sent
        calls = publisher.publish.call_args_list
        assert calls[0][0][0] == "messages.message_received"
        assert calls[1][0][0] == "messages.message_sent"
        assert calls[2][0][0] == "messages.message_received"
        assert calls[3][0][0] == "messages.message_sent"

        # Verify all events have same session_id
        for call in calls:
            event = call[0][1]
            assert event.entity_id == session_id

    @pytest.mark.asyncio
    async def test_publisher_handles_both_event_types_consistently(self, publisher):
        """Test that publisher handles both message_received and message_sent consistently"""
        session_id = "consistency-test-session"

        # Test data for both event types
        test_data = {"test": "data", "consistent": True}

        # Publish both event types
        await publisher.message_received(session_id, test_data)
        await publisher.message_sent(session_id, test_data)

        # Verify both events were published
        assert publisher.publish.call_count == 2

        received_call = publisher.publish.call_args_list[0]
        sent_call = publisher.publish.call_args_list[1]

        # Both should have same session_id and data
        assert received_call[0][1].entity_id == session_id
        assert sent_call[0][1].entity_id == session_id
        assert received_call[0][1].data == test_data
        assert sent_call[0][1].data == test_data

        # But different event types and channels
        assert received_call[0][1].event_type == "message_received"
        assert sent_call[0][1].event_type == "message_sent"
        assert received_call[0][0] == "messages.message_received"
        assert sent_call[0][0] == "messages.message_sent"

    def test_message_event_factory_methods_produce_correct_types(self):
        """Test that both factory methods produce correctly typed events"""
        session_id = "factory-test-session"
        test_data = {"factory": "test"}

        # Create events using factory methods
        received_event = MessageEvent.message_received(session_id, test_data)
        sent_event = MessageEvent.message_sent(session_id, test_data)

        # Verify both are MessageEvent instances
        assert isinstance(received_event, MessageEvent)
        assert isinstance(sent_event, MessageEvent)

        # Verify correct event types
        assert received_event.event_type == "message_received"
        assert sent_event.event_type == "message_sent"

        # Verify same session and data
        assert received_event.entity_id == session_id
        assert sent_event.entity_id == session_id
        assert received_event.data == test_data
        assert sent_event.data == test_data
