"""
API schemas for workflow management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.workflows.workflow import WorkflowStatus, StepStatus, StepType


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow"""

    name: str = Field(..., description="Workflow name", min_length=1, max_length=255)
    description: str = Field(..., description="Workflow description")
    created_by: Optional[str] = Field(None, description="User who created the workflow")
    timeout: Optional[float] = Field(
        None, description="Workflow timeout in seconds", gt=0
    )
    max_parallel_steps: int = Field(
        5, description="Maximum parallel steps", ge=1, le=20
    )
    auto_retry_failed: bool = Field(True, description="Auto-retry failed steps")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AddStepRequest(BaseModel):
    """Request to add a step to a workflow"""

    name: str = Field(..., description="Step name", min_length=1, max_length=255)
    step_type: StepType = Field(..., description="Step type")
    depends_on: Optional[List[str]] = Field(None, description="Step dependencies")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Step parameters")
    condition: Optional[str] = Field(None, description="Condition expression")
    timeout: Optional[float] = Field(None, description="Step timeout in seconds", gt=0)
    max_retries: int = Field(3, description="Maximum retry attempts", ge=0)

    # Task step parameters
    task_id: Optional[str] = Field(None, description="Existing task ID to execute")
    agent_id: Optional[str] = Field(None, description="Agent ID for task execution")
    required_tools: Optional[List[str]] = Field(
        None, description="Required tools for task"
    )

    # Integration step parameters
    integration_id: Optional[str] = Field(None, description="Integration ID")
    integration_method: Optional[str] = Field(
        None, description="HTTP method for integration"
    )
    integration_endpoint: Optional[str] = Field(
        None, description="Integration endpoint"
    )


class WorkflowStepResponse(BaseModel):
    """Response model for workflow step"""

    id: str
    name: str
    step_type: str
    status: str
    depends_on: List[str]
    parameters: Dict[str, Any]
    condition: Optional[str]
    timeout: Optional[float]
    retry_count: int
    max_retries: int

    # Task step fields
    task_id: Optional[str]
    agent_id: Optional[str]
    required_tools: List[str]

    # Integration step fields
    integration_id: Optional[str]
    integration_method: Optional[str]
    integration_endpoint: Optional[str]

    # Execution results
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time: Optional[float]


class WorkflowResponse(BaseModel):
    """Response model for workflow"""

    id: str
    name: str
    description: str
    status: str
    metadata: Dict[str, Any]
    created_by: Optional[str]
    timeout: Optional[float]
    max_parallel_steps: int
    auto_retry_failed: bool

    # Execution state
    total_steps: int
    completed_steps: int
    failed_steps: int
    running_steps: int

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time: Optional[float]

    # Results
    results: Dict[str, Any]
    error_message: Optional[str]


class WorkflowListResponse(BaseModel):
    """Response model for workflow list"""

    workflows: List[WorkflowResponse]
    total_count: int


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status"""

    id: str
    name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time: Optional[float]
    total_steps: int
    completed_steps: int
    failed_steps: int
    running_steps: int
    error_message: Optional[str]


class WorkflowStepsResponse(BaseModel):
    """Response model for workflow steps"""

    workflow_id: str
    steps: List[WorkflowStepResponse]


class WorkflowStatisticsResponse(BaseModel):
    """Response model for workflow statistics"""

    total_workflows: int
    active_workflows: int
    engine_running: bool
    by_status: Dict[str, int]
    average_execution_time: Optional[float]


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow"""

    workflow_id: str = Field(..., description="Workflow ID to execute")


class CreateSimpleTaskWorkflowRequest(BaseModel):
    """Request to create a simple task workflow"""

    name: str = Field(..., description="Workflow name", min_length=1, max_length=255)
    description: str = Field(..., description="Workflow description")
    created_by: Optional[str] = Field(None, description="User who created the workflow")
    tasks: List[Dict[str, Any]] = Field(..., description="List of tasks to execute")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Data Processing Pipeline",
                "description": "Process and analyze incoming data",
                "created_by": "user123",
                "tasks": [
                    {
                        "name": "Collect Data",
                        "agent_id": "agent-1",
                        "required_tools": ["database", "api"],
                        "parameters": {"source": "external_api"},
                        "timeout": 300,
                        "max_retries": 2,
                    },
                    {
                        "name": "Process Data",
                        "agent_id": "agent-2",
                        "required_tools": ["processor"],
                        "parameters": {"algorithm": "ml_model_v2"},
                        "timeout": 600,
                        "max_retries": 1,
                    },
                    {
                        "name": "Store Results",
                        "agent_id": "agent-1",
                        "required_tools": ["database"],
                        "parameters": {"table": "processed_data"},
                        "timeout": 60,
                        "max_retries": 3,
                    },
                ],
            }
        }


class WorkflowControlRequest(BaseModel):
    """Request for workflow control operations"""

    action: str = Field(
        ..., description="Control action", pattern="^(pause|resume|cancel)$"
    )


class WorkflowControlResponse(BaseModel):
    """Response for workflow control operations"""

    success: bool
    message: str
    workflow_id: str
    new_status: Optional[str] = None
