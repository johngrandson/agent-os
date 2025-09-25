"""Tests for simplified orchestration event handlers"""

import logging

import pytest
from app.events.core.registry import event_registry
from app.events.orchestration.handlers import (
    handle_task_completed,
    handle_task_created,
    handle_task_failed,
    orchestration_router,
    task_registry,
)
from app.events.orchestration.task_state import TaskStatus


class TestOrchestrationHandlers:
    """Test simplified orchestration event handlers"""

    def setup_method(self):
        """Clear registry before each test"""
        task_registry.clear()

    @pytest.mark.asyncio
    async def test_handle_task_created(self, caplog):
        """Test task created handler logs correctly and creates task in registry"""
        task_data = {
            "entity_id": "task-123",
            "event_type": "task_created",
            "data": {"agent_id": "agent-456", "task_type": "data_processing"},
        }

        with caplog.at_level(logging.DEBUG):
            await handle_task_created(task_data)

        # Check that correct log messages were generated
        assert "Task created: task-123" in caplog.text

        # Check that task was created in registry
        task = task_registry.get_task("task-123")
        assert task is not None
        assert task.agent_id == "agent-456"
        assert task.task_type == "data_processing"

    @pytest.mark.asyncio
    async def test_handle_task_completed(self, caplog):
        """Test task completed handler logs correctly and updates registry"""
        # First create the task
        task_registry.create_task(task_id="task-345")
        task_registry.update_task_status("task-345", TaskStatus.IN_PROGRESS)

        task_data = {
            "entity_id": "task-345",
            "event_type": "task_completed",
            "data": {"result": {"output": "success"}},
        }

        with caplog.at_level(logging.DEBUG):
            await handle_task_completed(task_data)

        # Check that correct log messages were generated
        assert "Task completed: task-345" in caplog.text

        # Check that task status was updated in registry
        task = task_registry.get_task("task-345")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"output": "success"}

    @pytest.mark.asyncio
    async def test_handle_task_failed(self, caplog):
        """Test task failed handler logs correctly and updates registry"""
        # First create the task
        task_registry.create_task(task_id="task-999")
        task_registry.update_task_status("task-999", TaskStatus.IN_PROGRESS)

        task_data = {
            "entity_id": "task-999",
            "event_type": "task_failed",
            "data": {"error": "Connection timeout"},
        }

        with caplog.at_level(logging.ERROR):
            await handle_task_failed(task_data)

        # Check that correct log messages were generated
        assert "Task failed: task-999 - Connection timeout" in caplog.text

        # Check that task status was updated in registry
        task = task_registry.get_task("task-999")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_handle_task_failed_with_unknown_error(self, caplog):
        """Test task failed handler with unknown error"""
        # First create the task
        task_registry.create_task(task_id="task-error")
        task_registry.update_task_status("task-error", TaskStatus.IN_PROGRESS)

        task_data = {"entity_id": "task-error", "event_type": "task_failed", "data": {}}

        with caplog.at_level(logging.ERROR):
            await handle_task_failed(task_data)

        # Check that unknown error was logged
        assert "Unknown error" in caplog.text

        # Check that task status was updated in registry
        task = task_registry.get_task("task-error")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Unknown error"

    @pytest.mark.asyncio
    async def test_handlers_with_missing_entity_id(self, caplog):
        """Test handlers gracefully handle missing entity_id"""
        task_data_no_id = {"event_type": "task_created", "data": {"agent_id": "agent-123"}}

        with caplog.at_level(logging.INFO):
            # Should not crash
            await handle_task_created(task_data_no_id)

        # Should still log, but with None entity_id
        assert "Task created: None" in caplog.text

    @pytest.mark.asyncio
    async def test_handlers_with_missing_data(self, caplog):
        """Test handlers gracefully handle missing data"""
        task_data_no_data = {"entity_id": "task-123", "event_type": "task_created"}

        # Should not crash
        await handle_task_created(task_data_no_data)

        # Should still create task with defaults
        task = task_registry.get_task("task-123")
        assert task is not None
        assert task.agent_id is None
        assert task.task_type == ""


class TestOrchestrationRouterRegistration:
    """Test orchestration router registration"""

    def test_orchestration_router_exists(self):
        """Test that orchestration router is created"""
        assert orchestration_router is not None

    def test_orchestration_router_registered_in_registry(self):
        """Test that orchestration router is registered with event registry"""
        assert "orchestration" in event_registry.get_all_routers()

    def test_can_get_orchestration_router_from_registry(self):
        """Test that we can retrieve orchestration router from event registry"""
        router = event_registry.get_router("orchestration")
        assert router is not None

    def test_orchestration_router_included_in_all_routers(self):
        """Test that orchestration router is included in all routers"""
        all_routers = event_registry.get_all_routers()
        assert "orchestration" in all_routers
        assert all_routers["orchestration"] == orchestration_router


class TestOrchestrationHandlersWithTaskRegistry:
    """Test orchestration handlers with task registry integration"""

    def setup_method(self):
        """Clear registry before each test"""
        task_registry.clear()

    @pytest.mark.asyncio
    async def test_handle_task_created_creates_task_in_registry(self):
        """Test that handle_task_created actually creates task in registry"""
        task_data = {
            "entity_id": "registry-task-1",
            "data": {
                "agent_id": "agent-123",
                "task_type": "processing",
                "dependencies": ["dep1", "dep2"],
                "data": {"input": "test"},
            },
        }

        await handle_task_created(task_data)

        # Verify task exists in registry
        task = task_registry.get_task("registry-task-1")
        assert task is not None
        assert task.task_id == "registry-task-1"
        assert task.agent_id == "agent-123"
        assert task.task_type == "processing"
        assert task.dependencies == {"dep1", "dep2"}
        assert task.data == {"input": "test"}

    @pytest.mark.asyncio
    async def test_handle_task_completed_updates_status_and_result(self):
        """Test that handle_task_completed updates both status and result"""
        # Create task first
        task_registry.create_task(task_id="complete-test")
        task_registry.update_task_status("complete-test", TaskStatus.IN_PROGRESS)

        task_data = {
            "entity_id": "complete-test",
            "data": {"result": {"output": "completed successfully", "count": 42}},
        }

        await handle_task_completed(task_data)

        # Verify both status and result were updated
        task = task_registry.get_task("complete-test")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"output": "completed successfully", "count": 42}

    @pytest.mark.asyncio
    async def test_handle_task_failed_updates_status_and_error(self):
        """Test that handle_task_failed updates both status and error"""
        # Create task first
        task_registry.create_task(task_id="fail-test")
        task_registry.update_task_status("fail-test", TaskStatus.IN_PROGRESS)

        task_data = {"entity_id": "fail-test", "data": {"error": "Database connection failed"}}

        await handle_task_failed(task_data)

        # Verify both status and error were updated
        task = task_registry.get_task("fail-test")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Database connection failed"
