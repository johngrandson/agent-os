"""Orchestration service for basic task coordination"""

import logging
import uuid
from enum import Enum
from typing import Any

from app.events.orchestration.publisher import OrchestrationEventPublisher
from app.events.orchestration.task_registry import TaskRegistry
from app.events.orchestration.task_state import TaskStatus


logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Basic workflow execution states"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimpleWorkflowExecution:
    """Basic workflow execution tracking"""

    def __init__(self, execution_id: str, workflow_name: str, task_ids: list[str]):
        self.execution_id = execution_id
        self.workflow_name = workflow_name
        self.task_ids = task_ids
        self.status = WorkflowStatus.RUNNING


class OrchestrationService:
    """Basic orchestration service for simple task coordination"""

    def __init__(
        self,
        task_registry: TaskRegistry,
        event_publisher: OrchestrationEventPublisher,
    ) -> None:
        self.task_registry = task_registry
        self.event_publisher = event_publisher
        self.executions: dict[str, SimpleWorkflowExecution] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def create_workflow(self, task_list: list[dict[str, Any]]) -> str:
        """Create a basic workflow from task list"""
        execution_id = str(uuid.uuid4())
        workflow_name = "Basic Workflow"

        task_ids = []

        # Create tasks from simple list
        for task_data in task_list:
            task = self.task_registry.create_task(
                task_type=task_data.get("task_type", "basic_task"),
                dependencies=set(task_data.get("depends_on", [])),
                data=task_data,
            )
            task_ids.append(task.task_id)

            # Publish task created event
            await self.event_publisher.publish_task_created(task.task_id, task.data)

        # Create execution tracking
        execution = SimpleWorkflowExecution(execution_id, workflow_name, task_ids)
        self.executions[execution_id] = execution

        self.logger.info(f"Created workflow execution {execution_id} with {len(task_ids)} tasks")
        return execution_id

    async def execute_workflow(self, execution_id: str) -> bool:
        """Execute workflow by processing ready tasks"""
        execution = self.executions.get(execution_id)
        if not execution:
            self.logger.warning(f"Execution {execution_id} not found")
            return False

        # Process ready tasks
        ready_tasks = self.task_registry.get_ready_tasks()
        execution_ready_tasks = [task for task in ready_tasks if task.task_id in execution.task_ids]

        for task in execution_ready_tasks:
            self.task_registry.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
            # Simulate task completion for demo
            self.task_registry.update_task_status(task.task_id, TaskStatus.COMPLETED)
            await self.event_publisher.publish_task_completed(task.task_id, {"result": "completed"})

        # Update execution status
        completed_tasks = self.task_registry.get_tasks_by_status(TaskStatus.COMPLETED)
        completed_ids = {task.task_id for task in completed_tasks}
        execution_task_ids = set(execution.task_ids)

        if execution_task_ids.issubset(completed_ids):
            execution.status = WorkflowStatus.COMPLETED
            return True

        return True
