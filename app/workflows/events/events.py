"""
Workflow domain event classes
"""

from typing import Dict, Any, Optional
from app.events.core import BaseEvent, EventPriority
from .types import WorkflowEventType


class WorkflowEvent(BaseEvent):
    """Workflow-related events"""

    workflow_id: str
    step_id: Optional[str] = None

    @classmethod
    def workflow_created(
        cls, workflow_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_CREATED,
            workflow_id=workflow_id,
            data=data or {},
            source="workflow_service",
        )

    @classmethod
    def workflow_started(
        cls, workflow_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            data=data or {},
            source="workflow_engine",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def workflow_completed(
        cls, workflow_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_COMPLETED,
            workflow_id=workflow_id,
            data=data or {},
            source="workflow_engine",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def workflow_failed(
        cls, workflow_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_FAILED,
            workflow_id=workflow_id,
            data=data or {},
            source="workflow_engine",
            priority=EventPriority.URGENT,
        )

    @classmethod
    def workflow_paused(cls, workflow_id: str) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_PAUSED,
            workflow_id=workflow_id,
            source="workflow_engine",
            priority=EventPriority.NORMAL,
        )

    @classmethod
    def workflow_resumed(cls, workflow_id: str) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_RESUMED,
            workflow_id=workflow_id,
            source="workflow_engine",
            priority=EventPriority.NORMAL,
        )

    @classmethod
    def workflow_cancelled(cls, workflow_id: str) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_CANCELLED,
            workflow_id=workflow_id,
            source="workflow_engine",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def workflow_deleted(cls, workflow_id: str) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_DELETED,
            workflow_id=workflow_id,
            source="workflow_service",
            priority=EventPriority.NORMAL,
        )

    @classmethod
    def step_started(
        cls, workflow_id: str, step_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_STEP_STARTED,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data or {},
            source="workflow_engine",
        )

    @classmethod
    def step_completed(
        cls, workflow_id: str, step_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_STEP_COMPLETED,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data or {},
            source="workflow_engine",
        )

    @classmethod
    def step_failed(
        cls, workflow_id: str, step_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_STEP_FAILED,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data or {},
            source="workflow_engine",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def engine_started(cls, data: Dict[str, Any] = None) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_ENGINE_STARTED,
            workflow_id="system",
            data=data or {},
            source="workflow_engine",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def engine_stopped(cls) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_ENGINE_STOPPED,
            workflow_id="system",
            source="workflow_engine",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def notification_sent(
        cls, workflow_id: str, data: Dict[str, Any] = None
    ) -> "WorkflowEvent":
        return cls(
            event_type=WorkflowEventType.WORKFLOW_NOTIFICATION_SENT,
            workflow_id=workflow_id,
            data=data or {},
            source="workflow_engine",
            priority=EventPriority.NORMAL,
        )
