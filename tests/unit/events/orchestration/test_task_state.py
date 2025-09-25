"""Tests for simplified task state management"""

from datetime import datetime

from app.events.orchestration.task_state import TaskState, TaskStatus


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_task_status_values(self):
        """Test all task status values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.READY.value == "ready"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestTaskState:
    """Test simplified TaskState dataclass"""

    def test_default_creation(self):
        """Test creating task with default values"""
        task = TaskState()

        assert task.task_id is not None
        assert len(task.task_id) > 0
        assert task.agent_id is None
        assert task.task_type == ""
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == set()
        assert task.data == {}
        assert task.result is None
        assert task.error is None
        assert isinstance(task.created_at, datetime)
        assert task.completed_at is None

    def test_creation_with_parameters(self):
        """Test creating task with specified parameters"""
        task_id = "task-123"
        agent_id = "agent-456"
        task_type = "data_processing"
        dependencies = {"dep1", "dep2"}
        data = {"input": "test_data"}

        task = TaskState(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            dependencies=dependencies,
            data=data,
        )

        assert task.task_id == task_id
        assert task.agent_id == agent_id
        assert task.task_type == task_type
        assert task.dependencies == dependencies
        assert task.data == data

    def test_update_status_to_in_progress(self):
        """Test updating task status to IN_PROGRESS"""
        task = TaskState(status=TaskStatus.READY)

        task.update_status(TaskStatus.IN_PROGRESS)

        assert task.status == TaskStatus.IN_PROGRESS

    def test_update_status_to_completed(self):
        """Test updating task status to COMPLETED"""
        task = TaskState(status=TaskStatus.IN_PROGRESS)

        task.update_status(TaskStatus.COMPLETED)

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_update_status_to_failed(self):
        """Test updating task status to FAILED"""
        task = TaskState(status=TaskStatus.IN_PROGRESS)

        task.update_status(TaskStatus.FAILED)

        assert task.status == TaskStatus.FAILED
        assert task.completed_at is not None

    def test_add_dependency(self):
        """Test adding a dependency to task"""
        task = TaskState()

        task.add_dependency("dep1")
        assert "dep1" in task.dependencies

        task.add_dependency("dep2")
        assert "dep1" in task.dependencies
        assert "dep2" in task.dependencies

    def test_remove_dependency(self):
        """Test removing a dependency from task"""
        task = TaskState(dependencies={"dep1", "dep2"})

        task.remove_dependency("dep1")
        assert "dep1" not in task.dependencies
        assert "dep2" in task.dependencies

        # Removing non-existent dependency should not raise error
        task.remove_dependency("nonexistent")

    def test_set_result(self):
        """Test setting task result"""
        task = TaskState()
        result = {"output": "success", "count": 42}

        task.set_result(result)
        assert task.result == result

    def test_set_error(self):
        """Test setting task error"""
        task = TaskState()
        error = "Connection timeout"

        task.set_error(error)
        assert task.error == error

    def test_serialization_methods(self):
        """Test to_dict and from_dict methods if they still exist"""
        task = TaskState(
            task_id="test-123",
            agent_id="agent-456",
            task_type="processing",
            dependencies={"dep1"},
            data={"key": "value"},
        )
        task.set_result({"output": "done"})

        # Test serialization
        task_dict = task.to_dict()
        assert isinstance(task_dict, dict)
        assert task_dict["task_id"] == "test-123"
        assert task_dict["agent_id"] == "agent-456"

        # Test deserialization
        restored_task = TaskState.from_dict(task_dict)
        assert restored_task.task_id == task.task_id
        assert restored_task.agent_id == task.agent_id
        assert restored_task.task_type == task.task_type
        assert restored_task.dependencies == task.dependencies
        assert restored_task.data == task.data
        assert restored_task.result == task.result
