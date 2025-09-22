"""
API routers for workflow management
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from dependency_injector.wiring import inject, Provide

from app.container import ApplicationContainer as Container
from app.workflows.service import WorkflowService
from app.workflows.workflow import WorkflowStatus, StepType
from app.workflows.api.schemas import (
    CreateWorkflowRequest,
    AddStepRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowStatusResponse,
    WorkflowStepsResponse,
    WorkflowStatisticsResponse,
    ExecuteWorkflowRequest,
    CreateSimpleTaskWorkflowRequest,
    WorkflowControlRequest,
    WorkflowControlResponse,
    WorkflowStepResponse,
)

router = APIRouter(tags=["workflows"])


@router.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=201,
    summary="Create workflow",
    description="Create a new workflow definition",
)
@inject
async def create_workflow(
    request: CreateWorkflowRequest,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Create a new workflow"""
    try:
        workflow = await workflow_service.create_workflow(
            name=request.name,
            description=request.description,
            created_by=request.created_by,
            timeout=request.timeout,
            max_parallel_steps=request.max_parallel_steps,
            auto_retry_failed=request.auto_retry_failed,
            metadata=request.metadata,
        )

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            metadata=workflow.metadata,
            created_by=workflow.created_by,
            timeout=workflow.timeout,
            max_parallel_steps=workflow.max_parallel_steps,
            auto_retry_failed=workflow.auto_retry_failed,
            total_steps=len(workflow.steps),
            completed_steps=len(workflow.completed_step_ids),
            failed_steps=len(workflow.failed_step_ids),
            running_steps=len(
                [s for s in workflow.steps.values() if s.status.value == "running"]
            ),
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            execution_time=workflow.execution_time,
            results=workflow.results,
            error_message=workflow.error_message,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/workflows/simple-task-workflow",
    response_model=WorkflowResponse,
    status_code=201,
    summary="Create simple task workflow",
    description="Create a workflow with sequential task execution",
)
@inject
async def create_simple_task_workflow(
    request: CreateSimpleTaskWorkflowRequest,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Create a simple task workflow"""
    try:
        workflow = await workflow_service.create_simple_task_workflow(
            name=request.name,
            description=request.description,
            tasks=request.tasks,
            created_by=request.created_by,
        )

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            metadata=workflow.metadata,
            created_by=workflow.created_by,
            timeout=workflow.timeout,
            max_parallel_steps=workflow.max_parallel_steps,
            auto_retry_failed=workflow.auto_retry_failed,
            total_steps=len(workflow.steps),
            completed_steps=len(workflow.completed_step_ids),
            failed_steps=len(workflow.failed_step_ids),
            running_steps=len(
                [s for s in workflow.steps.values() if s.status.value == "running"]
            ),
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            execution_time=workflow.execution_time,
            results=workflow.results,
            error_message=workflow.error_message,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    summary="List workflows",
    description="Get list of workflows with optional filtering",
)
@inject
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    limit: int = Query(50, description="Maximum number of workflows", ge=1, le=100),
    offset: int = Query(0, description="Number of workflows to skip", ge=0),
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """List workflows with filtering"""
    try:
        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = WorkflowStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        workflows = await workflow_service.list_workflows(
            status=status_filter,
            created_by=created_by,
            limit=limit,
            offset=offset,
        )

        workflow_responses = []
        for workflow in workflows:
            workflow_responses.append(
                WorkflowResponse(
                    id=workflow.id,
                    name=workflow.name,
                    description=workflow.description,
                    status=workflow.status.value,
                    metadata=workflow.metadata,
                    created_by=workflow.created_by,
                    timeout=workflow.timeout,
                    max_parallel_steps=workflow.max_parallel_steps,
                    auto_retry_failed=workflow.auto_retry_failed,
                    total_steps=len(workflow.steps),
                    completed_steps=len(workflow.completed_step_ids),
                    failed_steps=len(workflow.failed_step_ids),
                    running_steps=len(
                        [
                            s
                            for s in workflow.steps.values()
                            if s.status.value == "running"
                        ]
                    ),
                    created_at=workflow.created_at,
                    started_at=workflow.started_at,
                    completed_at=workflow.completed_at,
                    execution_time=workflow.execution_time,
                    results=workflow.results,
                    error_message=workflow.error_message,
                )
            )

        return WorkflowListResponse(
            workflows=workflow_responses, total_count=len(workflow_responses)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Get workflow",
    description="Get workflow by ID",
)
@inject
async def get_workflow(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Get workflow by ID"""
    workflow = await workflow_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status.value,
        metadata=workflow.metadata,
        created_by=workflow.created_by,
        timeout=workflow.timeout,
        max_parallel_steps=workflow.max_parallel_steps,
        auto_retry_failed=workflow.auto_retry_failed,
        total_steps=len(workflow.steps),
        completed_steps=len(workflow.completed_step_ids),
        failed_steps=len(workflow.failed_step_ids),
        running_steps=len(
            [s for s in workflow.steps.values() if s.status.value == "running"]
        ),
        created_at=workflow.created_at,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        execution_time=workflow.execution_time,
        results=workflow.results,
        error_message=workflow.error_message,
    )


@router.delete(
    "/workflows/{workflow_id}",
    summary="Delete workflow",
    description="Delete a workflow",
)
@inject
async def delete_workflow(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Delete a workflow"""
    success = await workflow_service.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {"message": "Workflow deleted successfully"}


@router.post(
    "/workflows/{workflow_id}/steps",
    response_model=WorkflowResponse,
    summary="Add step to workflow",
    description="Add a step to an existing workflow",
)
@inject
async def add_step_to_workflow(
    workflow_id: str,
    request: AddStepRequest,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Add a step to a workflow"""
    try:
        workflow = await workflow_service.add_step_to_workflow(
            workflow_id=workflow_id,
            step_name=request.name,
            step_type=request.step_type,
            depends_on=request.depends_on,
            parameters=request.parameters,
            condition=request.condition,
            timeout=request.timeout,
            max_retries=request.max_retries,
            task_id=request.task_id,
            agent_id=request.agent_id,
            required_tools=request.required_tools,
            integration_id=request.integration_id,
            integration_method=request.integration_method,
            integration_endpoint=request.integration_endpoint,
        )

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            metadata=workflow.metadata,
            created_by=workflow.created_by,
            timeout=workflow.timeout,
            max_parallel_steps=workflow.max_parallel_steps,
            auto_retry_failed=workflow.auto_retry_failed,
            total_steps=len(workflow.steps),
            completed_steps=len(workflow.completed_step_ids),
            failed_steps=len(workflow.failed_step_ids),
            running_steps=len(
                [s for s in workflow.steps.values() if s.status.value == "running"]
            ),
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            execution_time=workflow.execution_time,
            results=workflow.results,
            error_message=workflow.error_message,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/workflows/{workflow_id}/steps/{step_id}",
    response_model=WorkflowResponse,
    summary="Remove step from workflow",
    description="Remove a step from a workflow",
)
@inject
async def remove_step_from_workflow(
    workflow_id: str,
    step_id: str,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Remove a step from a workflow"""
    try:
        workflow = await workflow_service.remove_step_from_workflow(
            workflow_id, step_id
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow or step not found")

        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            metadata=workflow.metadata,
            created_by=workflow.created_by,
            timeout=workflow.timeout,
            max_parallel_steps=workflow.max_parallel_steps,
            auto_retry_failed=workflow.auto_retry_failed,
            total_steps=len(workflow.steps),
            completed_steps=len(workflow.completed_step_ids),
            failed_steps=len(workflow.failed_step_ids),
            running_steps=len(
                [s for s in workflow.steps.values() if s.status.value == "running"]
            ),
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            execution_time=workflow.execution_time,
            results=workflow.results,
            error_message=workflow.error_message,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workflows/{workflow_id}/execute",
    summary="Execute workflow",
    description="Start executing a workflow",
)
@inject
async def execute_workflow(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Execute a workflow"""
    try:
        success = await workflow_service.execute_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {"message": "Workflow execution started", "workflow_id": workflow_id}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/workflows/{workflow_id}/control",
    response_model=WorkflowControlResponse,
    summary="Control workflow",
    description="Pause, resume, or cancel a workflow",
)
@inject
async def control_workflow(
    workflow_id: str,
    request: WorkflowControlRequest,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Control workflow execution"""
    try:
        success = False
        new_status = None

        if request.action == "pause":
            success = await workflow_service.pause_workflow(workflow_id)
            new_status = "paused" if success else None
        elif request.action == "resume":
            success = await workflow_service.resume_workflow(workflow_id)
            new_status = "running" if success else None
        elif request.action == "cancel":
            success = await workflow_service.cancel_workflow(workflow_id)
            new_status = "cancelled" if success else None

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to {request.action} workflow {workflow_id}",
            )

        return WorkflowControlResponse(
            success=success,
            message=f"Workflow {request.action}ed successfully",
            workflow_id=workflow_id,
            new_status=new_status,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/workflows/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get workflow status",
    description="Get detailed workflow execution status",
)
@inject
async def get_workflow_status(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Get workflow status"""
    status = await workflow_service.get_workflow_status(workflow_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowStatusResponse(**status)


@router.get(
    "/workflows/{workflow_id}/steps",
    response_model=WorkflowStepsResponse,
    summary="Get workflow steps",
    description="Get all steps in a workflow with their status",
)
@inject
async def get_workflow_steps(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Get workflow steps"""
    steps_data = await workflow_service.get_workflow_steps(workflow_id)
    if steps_data is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps = [WorkflowStepResponse(**step) for step in steps_data]

    return WorkflowStepsResponse(
        workflow_id=workflow_id,
        steps=steps,
    )


@router.get(
    "/workflows/active/list",
    response_model=List[WorkflowStatusResponse],
    summary="List active workflows",
    description="Get all currently active workflows",
)
@inject
async def list_active_workflows(
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """List active workflows"""
    try:
        active_workflows = await workflow_service.list_active_workflows()
        return [WorkflowStatusResponse(**status) for status in active_workflows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/workflows/statistics",
    response_model=WorkflowStatisticsResponse,
    summary="Get workflow statistics",
    description="Get statistics about the workflow system",
)
@inject
async def get_workflow_statistics(
    workflow_service: WorkflowService = Depends(Provide[Container.workflow_service]),
):
    """Get workflow statistics"""
    try:
        stats = await workflow_service.get_workflow_statistics()
        return WorkflowStatisticsResponse(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
