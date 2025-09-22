"""
Task service for managing tasks and orchestration
"""

import uuid
import logging
from typing import List, Optional, Dict, Any

from app.tasks.repositories.task_repository import TaskRepository
from app.tasks.task import Task, TaskStatus, TaskType, TaskPriority
from app.tasks.api.schemas import CreateTaskCommand, UpdateTaskCommand
from app.agents.repositories.agent_repository import AgentRepository
from app.tools.registry import ToolRegistry
from app.events.bus import EventBus
from app.tasks.events import TaskEvent
from infrastructure.database import Transactional

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task management and orchestration"""

    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        agent_repository: AgentRepository,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
    ):
        self.task_repository = task_repository
        self.agent_repository = agent_repository
        self.event_bus = event_bus
        self.tool_registry = tool_registry

    async def get_task_list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        task_type: Optional[TaskType] = None,
        assigned_agent_id: Optional[str] = None,
        assigned_by: Optional[str] = None,
        include_subtasks: bool = True,
    ) -> List[Task]:
        """Get list of tasks with filtering"""
        agent_uuid = None
        if assigned_agent_id:
            try:
                agent_uuid = uuid.UUID(assigned_agent_id)
            except ValueError:
                return []

        return await self.task_repository.get_tasks(
            limit=limit,
            offset=offset,
            status=status,
            priority=priority,
            task_type=task_type,
            assigned_agent_id=agent_uuid,
            assigned_by=assigned_by,
            include_subtasks=include_subtasks,
        )

    @Transactional()
    async def create_task(self, *, command: CreateTaskCommand) -> Task:
        """Create a new task"""

        # Validate assigned agent if provided
        assigned_agent_uuid = None
        if command.assigned_agent_id:
            try:
                assigned_agent_uuid = uuid.UUID(command.assigned_agent_id)
                agent = await self.agent_repository.get_agent_by_id(
                    agent_id=assigned_agent_uuid
                )
                if not agent:
                    raise ValueError(f"Agent {command.assigned_agent_id} not found")
            except ValueError as e:
                raise ValueError(f"Invalid agent ID: {e}")

        # Validate parent task if provided
        parent_task_uuid = None
        if command.parent_task_id:
            try:
                parent_task_uuid = uuid.UUID(command.parent_task_id)
                parent_task = await self.task_repository.get_task_by_id(
                    task_id=parent_task_uuid
                )
                if not parent_task:
                    raise ValueError(f"Parent task {command.parent_task_id} not found")
            except ValueError as e:
                raise ValueError(f"Invalid parent task ID: {e}")

        # Validate expected tools
        if command.expected_tools:
            invalid_tools = [
                tool
                for tool in command.expected_tools
                if not self.tool_registry.get_tool(tool)
            ]
            if invalid_tools:
                logger.warning(f"Invalid tools specified: {invalid_tools}")

        task = Task.create(
            title=command.title,
            description=command.description,
            task_type=command.task_type,
            priority=command.priority,
            assigned_agent_id=assigned_agent_uuid,
            assigned_by=command.assigned_by,
            parent_task_id=parent_task_uuid,
            parameters=command.parameters,
            expected_tools=command.expected_tools,
        )

        await self.task_repository.save(task=task)

        # Emit task created event
        event = TaskEvent.task_created(
            task_id=str(task.id),
            data={
                "title": task.title,
                "task_type": task.task_type.value,
                "priority": task.priority.value,
                "assigned_agent_id": str(task.assigned_agent_id)
                if task.assigned_agent_id
                else None,
            },
        )
        await self.event_bus.emit(event)

        return task

    async def get_task_by_id(self, *, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        try:
            task_uuid = uuid.UUID(task_id)
            return await self.task_repository.get_task_by_id(task_id=task_uuid)
        except ValueError:
            return None

    @Transactional()
    async def update_task(self, *, command: UpdateTaskCommand) -> Optional[Task]:
        """Update an existing task"""
        task = await self.get_task_by_id(task_id=command.task_id)
        if not task:
            return None

        # Update fields if provided
        if command.title is not None:
            task.title = command.title
        if command.description is not None:
            task.description = command.description
        if command.task_type is not None:
            task.task_type = command.task_type
        if command.priority is not None:
            task.priority = command.priority
        if command.status is not None:
            task.status = command.status
        if command.assigned_by is not None:
            task.assigned_by = command.assigned_by
        if command.parameters is not None:
            task.parameters = command.parameters
        if command.expected_tools is not None:
            task.expected_tools = command.expected_tools
        if command.results is not None:
            task.results = command.results
        if command.error_message is not None:
            task.error_message = command.error_message

        # Handle agent assignment
        if command.assigned_agent_id is not None:
            if command.assigned_agent_id:
                try:
                    agent_uuid = uuid.UUID(command.assigned_agent_id)
                    agent = await self.agent_repository.get_agent_by_id(
                        agent_id=agent_uuid
                    )
                    if not agent:
                        raise ValueError(f"Agent {command.assigned_agent_id} not found")
                    task.assigned_agent_id = agent_uuid
                except ValueError as e:
                    raise ValueError(f"Invalid agent ID: {e}")
            else:
                task.assigned_agent_id = None

        await self.task_repository.update(task=task)
        return task

    @Transactional()
    async def delete_task(self, *, task_id: str) -> bool:
        """Delete a task by ID"""
        task = await self.get_task_by_id(task_id=task_id)
        if not task:
            return False

        await self.task_repository.delete(task=task)
        return True

    async def get_agent_tasks(
        self,
        *,
        agent_id: str,
        limit: int = 20,
        offset: int = 0,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """Get tasks assigned to a specific agent"""
        try:
            agent_uuid = uuid.UUID(agent_id)
            return await self.task_repository.get_tasks_by_agent(
                agent_id=agent_uuid, limit=limit, offset=offset, status=status
            )
        except ValueError:
            return []

    async def get_subtasks(
        self, *, parent_task_id: str, limit: int = 20, offset: int = 0
    ) -> List[Task]:
        """Get subtasks of a parent task"""
        try:
            parent_uuid = uuid.UUID(parent_task_id)
            return await self.task_repository.get_subtasks(
                parent_task_id=parent_uuid, limit=limit, offset=offset
            )
        except ValueError:
            return []

    async def get_pending_tasks(
        self, *, limit: int = 20, priority: Optional[TaskPriority] = None
    ) -> List[Task]:
        """Get pending tasks for assignment"""
        return await self.task_repository.get_pending_tasks(
            limit=limit, priority=priority
        )

    async def get_active_tasks(
        self, *, agent_id: Optional[str] = None, limit: int = 20
    ) -> List[Task]:
        """Get currently active tasks"""
        agent_uuid = None
        if agent_id:
            try:
                agent_uuid = uuid.UUID(agent_id)
            except ValueError:
                return []

        return await self.task_repository.get_active_tasks(
            agent_id=agent_uuid, limit=limit
        )

    async def assign_task(
        self, *, task_id: str, agent_id: str, assigned_by: Optional[str] = None
    ) -> Optional[Task]:
        """Assign a task to an agent"""
        task = await self.get_task_by_id(task_id=task_id)
        if not task:
            return None

        try:
            agent_uuid = uuid.UUID(agent_id)
            agent = await self.agent_repository.get_agent_by_id(agent_id=agent_uuid)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Check if agent has required tools
            if task.expected_tools and agent.available_tools:
                missing_tools = [
                    tool
                    for tool in task.expected_tools
                    if tool not in agent.available_tools
                ]
                if missing_tools:
                    logger.warning(
                        f"Agent {agent_id} is missing required tools: {missing_tools} for task {task_id}"
                    )

            task.assigned_agent_id = agent_uuid
            if assigned_by:
                task.assigned_by = assigned_by

            await self.task_repository.update(task=task)

            # Emit task assigned event
            event = TaskEvent.task_assigned(
                task_id=str(task.id), agent_id=agent_id, assigned_by=assigned_by
            )
            await self.event_bus.emit(event)

            return task

        except ValueError as e:
            raise ValueError(f"Invalid agent ID: {e}")

    @Transactional()
    async def execute_task(
        self,
        *,
        task_id: str,
        agent_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a task"""
        task = await self.get_task_by_id(task_id=task_id)
        if not task:
            return {"error": "Task not found"}

        # Assign agent if provided and not already assigned
        if agent_id and not task.assigned_agent_id:
            try:
                assigned_task = await self.assign_task(
                    task_id=task_id, agent_id=agent_id, assigned_by="system"
                )
                if not assigned_task:
                    return {"error": "Failed to assign agent to task"}
                task = assigned_task
            except ValueError as e:
                return {"error": str(e)}

        if not task.assigned_agent_id:
            return {"error": "Task has no assigned agent"}

        # Get the assigned agent
        agent = await self.agent_repository.get_agent_by_id(
            agent_id=task.assigned_agent_id
        )
        if not agent:
            return {"error": "Assigned agent not found"}

        # Start task execution
        task.start_execution()
        await self.task_repository.update(task=task)

        # Emit task started event
        start_event = TaskEvent.task_started(
            task_id=str(task.id), agent_id=str(agent.id)
        )
        await event_bus.emit(start_event)

        try:
            # Merge parameters
            execution_params = task.parameters or {}
            if parameters:
                execution_params.update(parameters)

            # Execute based on task type
            results = await self._execute_task_logic(
                task=task, agent=agent, parameters=execution_params, timeout=timeout
            )

            # Complete task
            task.complete_execution(results=results)
            await self.task_repository.update(task=task)

            # Emit task completed event
            complete_event = TaskEvent.task_completed(
                task_id=str(task.id), agent_id=str(agent.id), results=results
            )
            await event_bus.emit(complete_event)

            return {
                "task_id": str(task.id),
                "status": task.status.value,
                "results": results,
                "execution_time": task.execution_time,
                "agent_id": str(agent.id),
            }

        except Exception as e:
            # Fail task
            error_message = str(e)
            task.fail_execution(error_message=error_message)
            await self.task_repository.update(task=task)

            # Emit task failed event
            fail_event = TaskEvent.task_failed(
                task_id=str(task.id), agent_id=str(agent.id), error=error_message
            )
            await event_bus.emit(fail_event)

            logger.error(f"Task {task_id} execution failed: {error_message}")

            return {
                "task_id": str(task.id),
                "status": task.status.value,
                "error": error_message,
                "agent_id": str(agent.id),
            }

    async def _execute_task_logic(
        self,
        *,
        task: Task,
        agent,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute the actual task logic"""
        results = {"task_type": task.task_type.value}

        # Execute tools if specified
        if task.expected_tools:
            tool_results = {}
            for tool_name in task.expected_tools:
                if agent.available_tools and tool_name in agent.available_tools:
                    tool = self.tool_registry.get_tool(tool_name)
                    if tool:
                        try:
                            tool_result = await self.tool_registry.execute_tool(
                                tool_name=tool_name,
                                parameters=parameters,
                                timeout=timeout,
                            )
                            tool_results[tool_name] = {
                                "status": tool_result.status.value,
                                "data": tool_result.data,
                                "error": tool_result.error,
                                "execution_time": tool_result.execution_time,
                            }
                        except Exception as e:
                            tool_results[tool_name] = {
                                "status": "error",
                                "error": str(e),
                            }

            results["tool_results"] = tool_results

        # Add task-specific logic based on type
        if task.task_type == TaskType.RESEARCH:
            results["research_summary"] = "Research task completed"
        elif task.task_type == TaskType.ANALYSIS:
            results["analysis_summary"] = "Analysis task completed"
        elif task.task_type == TaskType.COMMUNICATION:
            results["communication_summary"] = "Communication task completed"

        results["completed"] = True
        return results

    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        stats = await self.task_repository.get_task_statistics()
        stats["total_tasks"] = sum(stats["by_status"].values())
        return stats

    async def count_tasks(
        self,
        *,
        status: Optional[TaskStatus] = None,
        assigned_agent_id: Optional[str] = None,
    ) -> int:
        """Count tasks with optional filtering"""
        agent_uuid = None
        if assigned_agent_id:
            try:
                agent_uuid = uuid.UUID(assigned_agent_id)
            except ValueError:
                return 0

        return await self.task_repository.count_tasks(
            status=status, assigned_agent_id=agent_uuid
        )
