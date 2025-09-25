"""Task state management for orchestration system"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Task lifecycle states"""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskState:
    """Represents the state of a task in the orchestration system"""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str | None = None
    task_type: str = ""
    status: TaskStatus = TaskStatus.PENDING
    dependencies: set[str] = field(default_factory=set)
    data: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def update_status(self, new_status: TaskStatus) -> None:
        """Update task status and timestamp"""
        self.status = new_status
        if new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            self.completed_at = datetime.now(UTC)

    def add_dependency(self, dependency_task_id: str) -> None:
        """Add a task dependency"""
        self.dependencies.add(dependency_task_id)

    def remove_dependency(self, dependency_task_id: str) -> None:
        """Remove a task dependency"""
        self.dependencies.discard(dependency_task_id)

    def set_result(self, result: dict[str, Any]) -> None:
        """Set task result data"""
        self.result = result

    def set_error(self, error: str) -> None:
        """Set task error message"""
        self.error = error

    def is_ready(self, completed_tasks: set[str]) -> bool:
        """Check if task is ready to be started (all dependencies completed)"""
        return self.status == TaskStatus.PENDING and self.dependencies.issubset(completed_tasks)

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if transition to new status is valid"""
        valid_transitions = {
            TaskStatus.PENDING: {TaskStatus.READY, TaskStatus.FAILED},
            TaskStatus.READY: {TaskStatus.IN_PROGRESS, TaskStatus.FAILED},
            TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED, TaskStatus.FAILED},
            TaskStatus.COMPLETED: set(),  # Terminal state
            TaskStatus.FAILED: {TaskStatus.PENDING},  # Can retry by going back to pending
        }

        return new_status in valid_transitions.get(self.status, set())

    def to_dict(self) -> dict[str, Any]:
        """Convert task state to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "dependencies": list(self.dependencies),
            "data": self.data,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskState":
        """Create TaskState from dictionary"""
        task_state = cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            task_type=data["task_type"],
            status=TaskStatus(data["status"]),
            dependencies=set(data["dependencies"]),
            data=data["data"],
            result=data["result"],
            error=data["error"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

        if data.get("completed_at"):
            task_state.completed_at = datetime.fromisoformat(data["completed_at"])

        return task_state
