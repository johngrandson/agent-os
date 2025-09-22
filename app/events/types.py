"""
Unified event types aggregating all domain-specific events
"""

from enum import Enum

# Import all domain-specific event types
from app.agents.events.types import AgentEventType
from app.tasks.events.types import TaskEventType
from app.tools.events.types import ToolEventType
from app.integrations.events.types import IntegrationEventType
from app.teams.events.types import TeamEventType
from app.knowledge.events.types import KnowledgeEventType
from app.workflows.events.types import WorkflowEventType


class EventType(str, Enum):
    """Unified event types aggregating all domain-specific events"""

    # Agent Events
    AGENT_CREATED = AgentEventType.AGENT_CREATED
    AGENT_UPDATED = AgentEventType.AGENT_UPDATED
    AGENT_DELETED = AgentEventType.AGENT_DELETED
    AGENT_ACTIVATED = AgentEventType.AGENT_ACTIVATED
    AGENT_DEACTIVATED = AgentEventType.AGENT_DEACTIVATED

    # Task Events
    TASK_CREATED = TaskEventType.TASK_CREATED
    TASK_ASSIGNED = TaskEventType.TASK_ASSIGNED
    TASK_STARTED = TaskEventType.TASK_STARTED
    TASK_COMPLETED = TaskEventType.TASK_COMPLETED
    TASK_FAILED = TaskEventType.TASK_FAILED
    TASK_CANCELLED = TaskEventType.TASK_CANCELLED

    # Tool Events
    TOOL_REGISTERED = ToolEventType.TOOL_REGISTERED
    TOOL_UNREGISTERED = ToolEventType.TOOL_UNREGISTERED
    TOOL_EXECUTED = ToolEventType.TOOL_EXECUTED
    TOOL_FAILED = ToolEventType.TOOL_FAILED

    # Integration Events
    INTEGRATION_CREATED = IntegrationEventType.INTEGRATION_CREATED
    INTEGRATION_UPDATED = IntegrationEventType.INTEGRATION_UPDATED
    INTEGRATION_DELETED = IntegrationEventType.INTEGRATION_DELETED
    INTEGRATION_REQUEST = IntegrationEventType.INTEGRATION_REQUEST

    # Team Events
    TEAM_CREATED = TeamEventType.TEAM_CREATED
    TEAM_UPDATED = TeamEventType.TEAM_UPDATED
    TEAM_DELETED = TeamEventType.TEAM_DELETED
    MEMBER_ADDED = TeamEventType.MEMBER_ADDED
    MEMBER_REMOVED = TeamEventType.MEMBER_REMOVED
    COORDINATION_STARTED = TeamEventType.COORDINATION_STARTED

    # Knowledge Events
    MEMORY_CREATED = KnowledgeEventType.MEMORY_CREATED
    MEMORY_UPDATED = KnowledgeEventType.MEMORY_UPDATED
    MEMORY_DELETED = KnowledgeEventType.MEMORY_DELETED
    MEMORY_ACCESSED = KnowledgeEventType.MEMORY_ACCESSED
    KNOWLEDGE_SEARCHED = KnowledgeEventType.KNOWLEDGE_SEARCHED

    # Workflow Events
    WORKFLOW_CREATED = WorkflowEventType.WORKFLOW_CREATED
    WORKFLOW_STARTED = WorkflowEventType.WORKFLOW_STARTED
    WORKFLOW_COMPLETED = WorkflowEventType.WORKFLOW_COMPLETED
    WORKFLOW_FAILED = WorkflowEventType.WORKFLOW_FAILED
    WORKFLOW_PAUSED = WorkflowEventType.WORKFLOW_PAUSED
    WORKFLOW_RESUMED = WorkflowEventType.WORKFLOW_RESUMED
    WORKFLOW_CANCELLED = WorkflowEventType.WORKFLOW_CANCELLED
    WORKFLOW_DELETED = WorkflowEventType.WORKFLOW_DELETED
    WORKFLOW_STEP_STARTED = WorkflowEventType.WORKFLOW_STEP_STARTED
    WORKFLOW_STEP_COMPLETED = WorkflowEventType.WORKFLOW_STEP_COMPLETED
    WORKFLOW_STEP_FAILED = WorkflowEventType.WORKFLOW_STEP_FAILED
    WORKFLOW_ENGINE_STARTED = WorkflowEventType.WORKFLOW_ENGINE_STARTED
    WORKFLOW_ENGINE_STOPPED = WorkflowEventType.WORKFLOW_ENGINE_STOPPED
    WORKFLOW_NOTIFICATION_SENT = WorkflowEventType.WORKFLOW_NOTIFICATION_SENT

    # System Events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"

    # AgentOS Events
    AGENT_OS_LOAD_AGENTS = "agent_os.load_agents"
