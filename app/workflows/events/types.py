"""
Workflow event types
"""

from enum import Enum


class WorkflowEventType(str, Enum):
    """Types of workflow-related events"""

    WORKFLOW_CREATED = "workflow.created"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    WORKFLOW_CANCELLED = "workflow.cancelled"
    WORKFLOW_DELETED = "workflow.deleted"
    WORKFLOW_STEP_STARTED = "workflow.step_started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_STEP_FAILED = "workflow.step_failed"
    WORKFLOW_ENGINE_STARTED = "workflow.engine_started"
    WORKFLOW_ENGINE_STOPPED = "workflow.engine_stopped"
    WORKFLOW_NOTIFICATION_SENT = "workflow.notification_sent"
