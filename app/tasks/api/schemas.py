"""
Task API schemas
"""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.tasks.task import TaskStatus, TaskPriority, TaskType


# Request Models
class CreateTaskRequest(BaseModel):
    """Task creation request"""

    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    task_type: TaskType = Field(..., description="Task type")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="Task priority")
    assigned_agent_id: Optional[str] = Field(None, description="Assigned agent ID")
    assigned_by: Optional[str] = Field(None, description="Who assigned the task")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Task parameters")
    expected_tools: Optional[List[str]] = Field(None, description="Expected tools")


class UpdateTaskRequest(BaseModel):
    """Task update request"""

    title: Optional[str] = Field(None, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    task_type: Optional[TaskType] = Field(None, description="Task type")
    priority: Optional[TaskPriority] = Field(None, description="Task priority")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    assigned_agent_id: Optional[str] = Field(None, description="Assigned agent ID")
    assigned_by: Optional[str] = Field(None, description="Who assigned the task")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Task parameters")
    expected_tools: Optional[List[str]] = Field(None, description="Expected tools")
    results: Optional[Dict[str, Any]] = Field(None, description="Task results")
    error_message: Optional[str] = Field(None, description="Error message")


class TaskExecutionRequest(BaseModel):
    """Task execution request"""

    agent_id: Optional[str] = Field(None, description="Agent to execute the task")
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Additional parameters"
    )
    timeout: Optional[float] = Field(None, description="Execution timeout")


# Response Models
class TaskResponse(BaseModel):
    """Task response"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    task_type: TaskType = Field(..., description="Task type")
    status: TaskStatus = Field(..., description="Task status")
    priority: TaskPriority = Field(..., description="Task priority")
    assigned_agent_id: Optional[str] = Field(None, description="Assigned agent ID")
    assigned_by: Optional[str] = Field(None, description="Who assigned the task")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Task parameters")
    expected_tools: Optional[List[str]] = Field(None, description="Expected tools")
    results: Optional[Dict[str, Any]] = Field(None, description="Task results")
    error_message: Optional[str] = Field(None, description="Error message")
    started_at: Optional[str] = Field(None, description="Started at")
    completed_at: Optional[str] = Field(None, description="Completed at")
    execution_time: Optional[float] = Field(None, description="Execution time")
    created_at: Optional[str] = Field(None, description="Created at")
    updated_at: Optional[str] = Field(None, description="Updated at")

    @field_validator("id", "assigned_agent_id", "parent_task_id", mode="before")
    @classmethod
    def validate_uuid_fields(cls, v):
        """Convert UUID to string"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class TaskWithSubtasksResponse(TaskResponse):
    """Task response with subtasks included"""

    subtasks: List[TaskResponse] = Field(default_factory=list, description="Subtasks")


class TaskExecutionResponse(BaseModel):
    """Task execution response"""

    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Execution status")
    results: Optional[Dict[str, Any]] = Field(None, description="Execution results")
    error_message: Optional[str] = Field(None, description="Error message")
    execution_time: Optional[float] = Field(None, description="Execution time")
    agent_id: Optional[str] = Field(None, description="Agent that executed the task")


class TaskListResponse(BaseModel):
    """Task list response with pagination"""

    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total_count: int = Field(..., description="Total number of tasks")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")


class TaskStatisticsResponse(BaseModel):
    """Task statistics response"""

    by_status: Dict[str, int] = Field(..., description="Count by status")
    by_priority: Dict[str, int] = Field(..., description="Count by priority")
    by_type: Dict[str, int] = Field(..., description="Count by type")
    total_tasks: int = Field(..., description="Total number of tasks")


class TaskMetadataResponse(BaseModel):
    """Task metadata response"""

    statuses: List[Dict[str, str]] = Field(..., description="Available statuses")
    priorities: List[Dict[str, str]] = Field(..., description="Available priorities")
    types: List[Dict[str, str]] = Field(..., description="Available task types")


# Command Models (for internal use)
class CreateTaskCommand(BaseModel):
    """Internal command for task creation"""

    title: str
    description: Optional[str] = None
    task_type: TaskType
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent_id: Optional[str] = None
    assigned_by: Optional[str] = None
    parent_task_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    expected_tools: Optional[List[str]] = None


class UpdateTaskCommand(BaseModel):
    """Internal command for task updates"""

    task_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    assigned_agent_id: Optional[str] = None
    assigned_by: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    expected_tools: Optional[List[str]] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
