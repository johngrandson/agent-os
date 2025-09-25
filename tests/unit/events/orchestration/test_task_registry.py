"""Tests for simplified task registry"""

import pytest
from app.events.orchestration.task_registry import TaskRegistry
from app.events.orchestration.task_state import TaskStatus


class TestTaskRegistry:
    """Test simplified TaskRegistry class with only core methods"""

    @pytest.fixture
    def registry(self):
        """Create a fresh TaskRegistry for each test"""
        return TaskRegistry()

    def test_create_task_with_defaults(self, registry):
        """Test creating task with default parameters"""
        task = registry.create_task()

        assert task.task_id is not None
        assert task.agent_id is None
        assert task.task_type == ""
        # Task with no dependencies should automatically be READY
        assert task.status == TaskStatus.READY
        assert task.dependencies == set()
        assert task.data == {}

        # Verify task is stored in registry
        retrieved = registry.get_task(task.task_id)
        assert retrieved == task

    def test_create_task_with_parameters(self, registry):
        """Test creating task with specified parameters"""
        task_id = "task-123"
        agent_id = "agent-456"
        task_type = "data_processing"
        dependencies = {"dep1", "dep2"}
        data = {"input": "test"}

        task = registry.create_task(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            dependencies=dependencies,
            data=data,
        )

        assert task.task_id == task_id
        assert task.agent_id == agent_id
        assert task.task_type == task_type
        # Task with dependencies should be PENDING initially
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == dependencies
        assert task.data == data

    def test_create_task_without_dependencies_is_ready(self, registry):
        """Test that tasks without dependencies are automatically READY"""
        task = registry.create_task(task_id="ready-task")
        assert task.status == TaskStatus.READY

    def test_create_task_with_dependencies_is_pending(self, registry):
        """Test that tasks with dependencies start as PENDING"""
        task = registry.create_task(task_id="pending-task", dependencies={"dep1"})
        assert task.status == TaskStatus.PENDING

    def test_get_task_existing(self, registry):
        """Test getting an existing task"""
        task_id = "test-task"
        created_task = registry.create_task(task_id=task_id)

        retrieved_task = registry.get_task(task_id)
        assert retrieved_task == created_task

    def test_get_task_nonexistent(self, registry):
        """Test getting a nonexistent task"""
        result = registry.get_task("nonexistent")
        assert result is None

    def test_update_task_status_valid_transition(self, registry):
        """Test updating task status with valid transition"""
        registry.create_task(task_id="test-task")

        # READY -> IN_PROGRESS
        success = registry.update_task_status("test-task", TaskStatus.IN_PROGRESS)
        assert success is True

        updated_task = registry.get_task("test-task")
        assert updated_task.status == TaskStatus.IN_PROGRESS

    def test_update_task_status_completed_with_result(self, registry):
        """Test updating task status to completed with result"""
        registry.create_task(task_id="test-task")
        registry.update_task_status("test-task", TaskStatus.IN_PROGRESS)

        result_data = {"output": "success", "count": 42}
        success = registry.update_task_status("test-task", TaskStatus.COMPLETED, result=result_data)
        assert success is True

        updated_task = registry.get_task("test-task")
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.result == result_data

    def test_update_task_status_failed_with_error(self, registry):
        """Test updating task status to failed with error"""
        registry.create_task(task_id="test-task")
        registry.update_task_status("test-task", TaskStatus.IN_PROGRESS)

        error_msg = "Connection timeout"
        success = registry.update_task_status("test-task", TaskStatus.FAILED, error=error_msg)
        assert success is True

        updated_task = registry.get_task("test-task")
        assert updated_task.status == TaskStatus.FAILED
        assert updated_task.error == error_msg

    def test_update_task_status_nonexistent_task(self, registry):
        """Test updating status of nonexistent task"""
        success = registry.update_task_status("nonexistent", TaskStatus.COMPLETED)
        assert success is False

    def test_get_ready_tasks_empty_registry(self, registry):
        """Test getting ready tasks from empty registry"""
        ready_tasks = registry.get_ready_tasks()
        assert ready_tasks == []

    def test_get_ready_tasks(self, registry):
        """Test getting ready tasks"""
        # Create tasks with different statuses
        registry.create_task(task_id="ready-1")  # No deps = READY
        registry.create_task(task_id="ready-2")  # No deps = READY
        registry.create_task(task_id="pending", dependencies={"dep1"})  # Has deps = PENDING
        registry.create_task(task_id="in-progress")
        registry.update_task_status("in-progress", TaskStatus.IN_PROGRESS)

        ready_tasks = registry.get_ready_tasks()
        ready_task_ids = [task.task_id for task in ready_tasks]

        assert len(ready_tasks) == 2
        assert "ready-1" in ready_task_ids
        assert "ready-2" in ready_task_ids
        assert "pending" not in ready_task_ids
        assert "in-progress" not in ready_task_ids

    def test_get_tasks_by_status(self, registry):
        """Test getting tasks filtered by status"""
        # Create tasks with different statuses
        registry.create_task(task_id="ready")
        registry.create_task(task_id="pending", dependencies={"dep1"})
        registry.create_task(task_id="in-progress")
        registry.update_task_status("in-progress", TaskStatus.IN_PROGRESS)

        # Test filtering by READY status
        ready_tasks = registry.get_tasks_by_status(TaskStatus.READY)
        assert len(ready_tasks) == 1
        assert ready_tasks[0].task_id == "ready"

        # Test filtering by PENDING status
        pending_tasks = registry.get_tasks_by_status(TaskStatus.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0].task_id == "pending"

        # Test filtering by IN_PROGRESS status
        in_progress_tasks = registry.get_tasks_by_status(TaskStatus.IN_PROGRESS)
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].task_id == "in-progress"

        # Test filtering by non-existent status
        completed_tasks = registry.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(completed_tasks) == 0

    def test_clear_registry(self, registry):
        """Test clearing the registry"""
        # Create some tasks
        registry.create_task(task_id="task1")
        registry.create_task(task_id="task2")

        # Verify tasks exist
        assert registry.get_task("task1") is not None
        assert registry.get_task("task2") is not None

        # Clear registry
        registry.clear()

        # Verify tasks are gone
        assert registry.get_task("task1") is None
        assert registry.get_task("task2") is None
        assert registry.get_ready_tasks() == []
