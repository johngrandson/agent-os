"""Tests for orchestration events and publisher"""

from unittest.mock import AsyncMock, Mock

import pytest
from app.events.orchestration.events import OrchestrationEvent
from app.events.orchestration.publisher import OrchestrationEventPublisher


class TestOrchestrationEvent:
    """Test OrchestrationEvent class methods"""

    def test_task_created_event(self):
        """Test creating a task_created event"""
        task_id = "task-123"
        task_data = {"agent_id": "agent-456", "task_type": "data_processing"}

        event = OrchestrationEvent.task_created(task_id, task_data)

        assert event.entity_id == task_id
        assert event.event_type == "task_created"
        assert event.data == task_data

    def test_task_completed_event(self):
        """Test creating a task_completed event"""
        task_id = "task-345"
        task_data = {"agent_id": "agent-678", "result": "success", "duration": 120}

        event = OrchestrationEvent.task_completed(task_id, task_data)

        assert event.entity_id == task_id
        assert event.event_type == "task_completed"
        assert event.data == task_data

    def test_task_failed_event(self):
        """Test creating a task_failed event"""
        task_id = "task-999"
        task_data = {"agent_id": "agent-888", "error": "Connection timeout", "retry_count": 3}

        event = OrchestrationEvent.task_failed(task_id, task_data)

        assert event.entity_id == task_id
        assert event.event_type == "task_failed"
        assert event.data == task_data

    def test_event_with_empty_data(self):
        """Test creating events with empty data"""
        task_id = "task-empty"

        event = OrchestrationEvent.task_created(task_id, {})

        assert event.entity_id == task_id
        assert event.event_type == "task_created"
        assert event.data == {}


class TestOrchestrationEventPublisher:
    """Test OrchestrationEventPublisher class"""

    @pytest.fixture
    def mock_broker(self):
        """Create a mock broker for testing"""
        broker = Mock()
        broker.publish = AsyncMock()
        return broker

    @pytest.fixture
    def publisher(self, mock_broker):
        """Create OrchestrationEventPublisher with mock broker"""
        return OrchestrationEventPublisher(mock_broker)

    def test_get_domain_prefix(self, publisher):
        """Test that publisher returns correct domain prefix"""
        assert publisher.get_domain_prefix() == "orchestration"

    @pytest.mark.asyncio
    async def test_task_created_publication(self, publisher, mock_broker):
        """Test publishing task_created event"""
        task_id = "task-123"
        task_data = {"agent_id": "agent-456", "task_type": "data_processing"}

        await publisher.task_created(task_id, task_data)

        # Verify broker.publish was called
        mock_broker.publish.assert_called_once()

        # Get the call arguments
        call_args = mock_broker.publish.call_args
        published_data = call_args[0][0]
        channel = call_args[1]["channel"]

        # Verify the published data structure
        assert published_data["entity_id"] == task_id
        assert published_data["event_type"] == "task_created"
        assert published_data["data"] == task_data
        assert channel == "orchestration.task_created"

    @pytest.mark.asyncio
    async def test_task_completed_publication(self, publisher, mock_broker):
        """Test publishing task_completed event"""
        task_id = "task-345"
        task_data = {"agent_id": "agent-678", "result": "success", "duration": 120}

        await publisher.task_completed(task_id, task_data)

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args
        published_data = call_args[0][0]
        channel = call_args[1]["channel"]

        assert published_data["entity_id"] == task_id
        assert published_data["event_type"] == "task_completed"
        assert published_data["data"] == task_data
        assert channel == "orchestration.task_completed"

    @pytest.mark.asyncio
    async def test_task_failed_publication(self, publisher, mock_broker):
        """Test publishing task_failed event"""
        task_id = "task-999"
        task_data = {"agent_id": "agent-888", "error": "Connection timeout", "retry_count": 3}

        await publisher.task_failed(task_id, task_data)

        mock_broker.publish.assert_called_once()
        call_args = mock_broker.publish.call_args
        published_data = call_args[0][0]
        channel = call_args[1]["channel"]

        assert published_data["entity_id"] == task_id
        assert published_data["event_type"] == "task_failed"
        assert published_data["data"] == task_data
        assert channel == "orchestration.task_failed"

    @pytest.mark.asyncio
    async def test_publication_with_broker_error(self, publisher, mock_broker):
        """Test handling of broker publication errors"""
        task_id = "task-error"
        task_data = {"test": "data"}

        # Mock broker to raise an exception
        mock_broker.publish.side_effect = Exception("Redis connection failed")

        # Should raise the exception
        with pytest.raises(Exception, match="Redis connection failed"):
            await publisher.task_created(task_id, task_data)

    @pytest.mark.asyncio
    async def test_multiple_event_publications(self, publisher, mock_broker):
        """Test publishing multiple different events"""
        task_id = "task-multi"

        # Publish core event types only
        await publisher.task_created(task_id, {"created": True})
        await publisher.task_completed(task_id, {"completed": True})
        await publisher.task_failed(task_id, {"failed": True})

        # Verify all events were published
        assert mock_broker.publish.call_count == 3

        # Verify channels are correct
        call_channels = [call.kwargs["channel"] for call in mock_broker.publish.call_args_list]
        expected_channels = [
            "orchestration.task_created",
            "orchestration.task_completed",
            "orchestration.task_failed",
        ]
        assert call_channels == expected_channels
