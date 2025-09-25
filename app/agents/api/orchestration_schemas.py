"""Orchestration API schemas - basic request/response models"""

from typing import Any

from pydantic import BaseModel, Field


# Request Models
class CreateWorkflowRequest(BaseModel):
    """Request to create a workflow from a simple task list"""

    task_list: list[dict[str, Any]] = Field(
        ..., description="List of task definitions with their dependencies and data", min_items=1
    )


# Response Models
class CreateWorkflowResponse(BaseModel):
    """Response after creating a workflow"""

    execution_id: str = Field(..., description="Unique execution ID for the workflow")
    message: str = Field(..., description="Success message")


class WorkflowExecutionResponse(BaseModel):
    """Response for workflow execution requests"""

    execution_id: str = Field(..., description="Workflow execution ID")
    success: bool = Field(..., description="Whether execution started successfully")
    message: str = Field(..., description="Execution message")


class WorkflowHealthResponse(BaseModel):
    """Response for orchestration service health check"""

    status: str = Field(..., description="Service health status")
    message: str = Field(..., description="Health check message")


class WorkflowValidationResponse(BaseModel):
    """Response for workflow validation"""

    valid: bool = Field(..., description="Whether the workflow is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    message: str = Field(..., description="Validation summary message")
