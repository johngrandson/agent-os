"""Orchestration domain events"""

from dataclasses import dataclass

from app.events.core.base import BaseEvent


@dataclass
class OrchestrationEvent(BaseEvent):
    """Orchestration-specific event for task coordination"""

    @classmethod
    def task_created(cls, task_id: str, task_data: dict) -> "OrchestrationEvent":
        """Create task created event"""
        return cls(entity_id=task_id, event_type="task_created", data=task_data)

    @classmethod
    def task_completed(cls, task_id: str, task_data: dict) -> "OrchestrationEvent":
        """Create task completed event"""
        return cls(entity_id=task_id, event_type="task_completed", data=task_data)

    @classmethod
    def task_failed(cls, task_id: str, task_data: dict) -> "OrchestrationEvent":
        """Create task failed event"""
        return cls(entity_id=task_id, event_type="task_failed", data=task_data)
