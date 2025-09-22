"""
Task domain event classes
"""

from typing import Dict, Any, Optional
from app.events.core import BaseEvent, EventPriority
from .types import TaskEventType


class TaskEvent(BaseEvent):
    """Task-related events"""

    task_id: str
    agent_id: Optional[str] = None

    @classmethod
    def task_created(cls, task_id: str, data: Dict[str, Any] = None) -> "TaskEvent":
        return cls(
            event_type=TaskEventType.TASK_CREATED,
            task_id=task_id,
            data=data or {},
            source="task_service",
        )

    @classmethod
    def task_assigned(
        cls, task_id: str, agent_id: str, assigned_by: str = None
    ) -> "TaskEvent":
        return cls(
            event_type=TaskEventType.TASK_ASSIGNED,
            task_id=task_id,
            agent_id=agent_id,
            data={"assigned_by": assigned_by},
            source="task_service",
            target=agent_id,
        )

    @classmethod
    def task_started(cls, task_id: str, agent_id: str) -> "TaskEvent":
        return cls(
            event_type=TaskEventType.TASK_STARTED,
            task_id=task_id,
            agent_id=agent_id,
            source=agent_id,
            priority=EventPriority.HIGH,
        )

    @classmethod
    def task_completed(
        cls, task_id: str, agent_id: str, results: Dict[str, Any] = None
    ) -> "TaskEvent":
        return cls(
            event_type=TaskEventType.TASK_COMPLETED,
            task_id=task_id,
            agent_id=agent_id,
            data={"results": results or {}},
            source=agent_id,
            priority=EventPriority.HIGH,
        )

    @classmethod
    def task_failed(cls, task_id: str, agent_id: str, error: str) -> "TaskEvent":
        return cls(
            event_type=TaskEventType.TASK_FAILED,
            task_id=task_id,
            agent_id=agent_id,
            data={"error": error},
            source=agent_id,
            priority=EventPriority.URGENT,
        )
