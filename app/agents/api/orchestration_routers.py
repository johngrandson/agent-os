"""Orchestration API routers - basic workflow management endpoints"""

from app.agents.api.orchestration_schemas import (
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    WorkflowExecutionResponse,
    WorkflowHealthResponse,
    WorkflowValidationResponse,
)
from app.agents.services.orchestration_service import OrchestrationService
from app.container import Container
from dependency_injector.wiring import Provide, inject

from fastapi import APIRouter, Depends, HTTPException, Path


orchestration_router = APIRouter()


@orchestration_router.post(
    "/workflows",
    response_model=CreateWorkflowResponse,
    status_code=201,
    summary="Create a workflow from task list",
)
@inject
async def create_workflow(
    request: CreateWorkflowRequest,
    orchestration_service: OrchestrationService = Depends(Provide[Container.orchestration_service]),
) -> CreateWorkflowResponse:
    """Create a new workflow from a simple task list"""
    try:
        execution_id = await orchestration_service.create_workflow(request.task_list)
        return CreateWorkflowResponse(
            execution_id=execution_id, message="Workflow created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@orchestration_router.post(
    "/workflows/{execution_id}/execute",
    response_model=WorkflowExecutionResponse,
    summary="Execute a workflow by execution ID",
)
@inject
async def execute_workflow(
    execution_id: str = Path(..., description="Workflow execution ID"),
    orchestration_service: OrchestrationService = Depends(Provide[Container.orchestration_service]),
) -> WorkflowExecutionResponse:
    """Execute a workflow by processing ready tasks"""
    try:
        success = await orchestration_service.execute_workflow(execution_id)
        return WorkflowExecutionResponse(
            execution_id=execution_id,
            success=success,
            message="Workflow execution processed" if success else "Workflow execution failed",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@orchestration_router.get(
    "/health",
    response_model=WorkflowHealthResponse,
    summary="Check orchestration service health",
)
async def health_check() -> WorkflowHealthResponse:
    """Check the health of the orchestration service"""
    try:
        return WorkflowHealthResponse(status="healthy", message="Orchestration service is running")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get health status") from e


@orchestration_router.post(
    "/validate",
    response_model=WorkflowValidationResponse,
    summary="Validate workflow definition",
)
async def validate_workflow(request: CreateWorkflowRequest) -> WorkflowValidationResponse:
    """Validate a workflow definition"""
    try:
        # Simple validation - check that task_list is not empty
        if not request.task_list:
            return WorkflowValidationResponse(
                valid=False,
                errors=["Task list cannot be empty"],
                message="Workflow validation failed",
            )

        # Add more validation logic as needed
        return WorkflowValidationResponse(
            valid=True, errors=[], message="Workflow validation successful"
        )
    except Exception as e:
        return WorkflowValidationResponse(
            valid=False, errors=[str(e)], message="Workflow validation failed"
        )
