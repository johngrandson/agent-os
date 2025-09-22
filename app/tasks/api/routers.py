"""
Task API routers
"""

from typing import Optional, List
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, HTTPException

from app.container import ApplicationContainer as Container
from app.tasks.api.schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskExecutionRequest,
    TaskResponse,
    TaskWithSubtasksResponse,
    TaskExecutionResponse,
    TaskListResponse,
    TaskStatisticsResponse,
    TaskMetadataResponse,
    CreateTaskCommand,
    UpdateTaskCommand,
)
from app.tasks.task import TaskStatus, TaskPriority, TaskType
from app.tasks.services.task_service import TaskService

router = APIRouter(tags=["tasks"])


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    summary="Get list of tasks",
    description="Retrieve a paginated list of tasks with optional filtering",
)
@inject
async def get_task_list(
    limit: int = Query(
        20, description="Maximum number of tasks to return", ge=1, le=100
    ),
    offset: int = Query(0, description="Number of tasks to skip", ge=0),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(
        None, description="Filter by task priority"
    ),
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    assigned_agent_id: Optional[str] = Query(
        None, description="Filter by assigned agent ID"
    ),
    assigned_by: Optional[str] = Query(
        None, description="Filter by who assigned the task"
    ),
    include_subtasks: bool = Query(True, description="Include subtasks in the results"),
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Get paginated list of tasks with optional filtering"""
    tasks = await task_service.get_task_list(
        limit=limit,
        offset=offset,
        status=status,
        priority=priority,
        task_type=task_type,
        assigned_agent_id=assigned_agent_id,
        assigned_by=assigned_by,
        include_subtasks=include_subtasks,
    )

    # Get total count for pagination
    total_count = await task_service.count_tasks()

    task_responses = [TaskResponse.model_validate(task) for task in tasks]

    return TaskListResponse(
        tasks=task_responses,
        total_count=total_count,
        page=(offset // limit) + 1 if limit > 0 else 1,
        limit=limit,
    )


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a new task",
    description="Create a new task with optional agent assignment",
)
@inject
async def create_task(
    request: CreateTaskRequest,
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Create a new task"""
    try:
        command = CreateTaskCommand(
            title=request.title,
            description=request.description,
            task_type=request.task_type,
            priority=request.priority,
            assigned_agent_id=request.assigned_agent_id,
            assigned_by=request.assigned_by,
            parent_task_id=request.parent_task_id,
            parameters=request.parameters,
            expected_tools=request.expected_tools,
        )

        task = await task_service.create_task(command=command)
        return TaskResponse.model_validate(task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskWithSubtasksResponse,
    summary="Get a task by ID",
    description="Get detailed information about a specific task including subtasks",
)
@inject
async def get_task(
    task_id: str, task_service: TaskService = Depends(Provide[Container.task_service])
):
    """Get a task by ID"""
    task = await task_service.get_task_by_id(task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get subtasks
    subtasks = await task_service.get_subtasks(parent_task_id=task_id)
    subtask_responses = [TaskResponse.model_validate(subtask) for subtask in subtasks]

    task_response = TaskResponse.model_validate(task)
    return TaskWithSubtasksResponse(
        **task_response.model_dump(), subtasks=subtask_responses
    )


@router.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    description="Update an existing task",
)
@inject
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Update an existing task"""
    try:
        command = UpdateTaskCommand(
            task_id=task_id,
            title=request.title,
            description=request.description,
            task_type=request.task_type,
            priority=request.priority,
            status=request.status,
            assigned_agent_id=request.assigned_agent_id,
            assigned_by=request.assigned_by,
            parameters=request.parameters,
            expected_tools=request.expected_tools,
            results=request.results,
            error_message=request.error_message,
        )

        updated_task = await task_service.update_task(command=command)
        if not updated_task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse.model_validate(updated_task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
    description="Delete a task and all its subtasks",
)
@inject
async def delete_task(
    task_id: str, task_service: TaskService = Depends(Provide[Container.task_service])
):
    """Delete a task by ID"""
    success = await task_service.delete_task(task_id=task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post(
    "/tasks/{task_id}/assign",
    response_model=TaskResponse,
    summary="Assign task to agent",
    description="Assign a task to a specific agent",
)
@inject
async def assign_task(
    task_id: str,
    agent_id: str = Query(..., description="Agent ID to assign the task to"),
    assigned_by: Optional[str] = Query(None, description="Who is assigning the task"),
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Assign a task to an agent"""
    try:
        task = await task_service.assign_task(
            task_id=task_id, agent_id=agent_id, assigned_by=assigned_by
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse.model_validate(task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/tasks/{task_id}/execute",
    response_model=TaskExecutionResponse,
    summary="Execute a task",
    description="Execute a task with an optional agent",
)
@inject
async def execute_task(
    task_id: str,
    request: TaskExecutionRequest,
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Execute a task"""
    result = await task_service.execute_task(
        task_id=task_id,
        agent_id=request.agent_id,
        parameters=request.parameters,
        timeout=request.timeout,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return TaskExecutionResponse(**result)


@router.get(
    "/agents/{agent_id}/tasks",
    response_model=List[TaskResponse],
    summary="Get agent tasks",
    description="Get all tasks assigned to a specific agent",
)
@inject
async def get_agent_tasks(
    agent_id: str,
    limit: int = Query(
        20, description="Maximum number of tasks to return", ge=1, le=100
    ),
    offset: int = Query(0, description="Number of tasks to skip", ge=0),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Get tasks assigned to a specific agent"""
    tasks = await task_service.get_agent_tasks(
        agent_id=agent_id, limit=limit, offset=offset, status=status
    )

    return [TaskResponse.model_validate(task) for task in tasks]


@router.get(
    "/tasks/pending",
    response_model=List[TaskResponse],
    summary="Get pending tasks",
    description="Get all pending tasks for assignment",
)
@inject
async def get_pending_tasks(
    limit: int = Query(
        20, description="Maximum number of tasks to return", ge=1, le=100
    ),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Get pending tasks for assignment"""
    tasks = await task_service.get_pending_tasks(limit=limit, priority=priority)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get(
    "/tasks/active",
    response_model=List[TaskResponse],
    summary="Get active tasks",
    description="Get all currently active (in progress) tasks",
)
@inject
async def get_active_tasks(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(
        20, description="Maximum number of tasks to return", ge=1, le=100
    ),
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Get currently active tasks"""
    tasks = await task_service.get_active_tasks(agent_id=agent_id, limit=limit)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get(
    "/tasks/statistics",
    response_model=TaskStatisticsResponse,
    summary="Get task statistics",
    description="Get statistics about tasks by status, priority, and type",
)
@inject
async def get_task_statistics(
    task_service: TaskService = Depends(Provide[Container.task_service]),
):
    """Get task statistics"""
    stats = await task_service.get_task_statistics()
    return TaskStatisticsResponse(**stats)


@router.get(
    "/tasks/metadata",
    response_model=TaskMetadataResponse,
    summary="Get task metadata",
    description="Get available task statuses, priorities, and types",
)
async def get_task_metadata():
    """Get task metadata"""
    statuses = [
        {"value": status.value, "name": status.value.replace("_", " ").title()}
        for status in TaskStatus
    ]
    priorities = [
        {"value": priority.value, "name": priority.value.replace("_", " ").title()}
        for priority in TaskPriority
    ]
    types = [
        {"value": task_type.value, "name": task_type.value.replace("_", " ").title()}
        for task_type in TaskType
    ]

    return TaskMetadataResponse(statuses=statuses, priorities=priorities, types=types)
