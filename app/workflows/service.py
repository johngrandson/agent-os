"""
Workflow service for managing workflow execution and persistence
"""

import uuid
import logging
from typing import List, Optional, Dict, Any

from app.workflows.workflow import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepType,
    StepStatus,
)
from app.workflows.engine import WorkflowEngine
from app.workflows.repository import workflow_repository
from app.events.bus import EventBus
from app.workflows.events import WorkflowEvent

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflow management and orchestration"""

    def __init__(self, workflow_engine: WorkflowEngine, event_bus: EventBus):
        self.workflow_engine = workflow_engine
        self.event_bus = event_bus

    async def create_workflow(
        self,
        name: str,
        description: str,
        created_by: Optional[str] = None,
        timeout: Optional[float] = None,
        max_parallel_steps: int = 5,
        auto_retry_failed: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """Create a new workflow"""
        workflow = Workflow.create(
            name=name,
            description=description,
            created_by=created_by,
        )

        if timeout:
            workflow.timeout = timeout
        workflow.max_parallel_steps = max_parallel_steps
        workflow.auto_retry_failed = auto_retry_failed
        if metadata:
            workflow.metadata = metadata

        # Save to database
        await workflow_repository.save_workflow(workflow)

        # Emit workflow created event
        await self.event_bus.emit(
            WorkflowEvent.workflow_created(
                workflow_id=workflow.id,
                data={
                    "name": workflow.name,
                    "created_by": workflow.created_by,
                    "total_steps": len(workflow.steps),
                },
            )
        )

        logger.info(f"Created workflow {workflow.id}: {workflow.name}")
        return workflow

    async def add_step_to_workflow(
        self,
        workflow_id: str,
        step_name: str,
        step_type: StepType,
        depends_on: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        condition: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        # Task step parameters
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        required_tools: Optional[List[str]] = None,
        # Integration step parameters
        integration_id: Optional[str] = None,
        integration_method: Optional[str] = None,
        integration_endpoint: Optional[str] = None,
    ) -> Optional[Workflow]:
        """Add a step to an existing workflow"""
        workflow = await workflow_repository.get_workflow_by_id(workflow_id)
        if not workflow:
            return None

        # Don't allow modification of running workflows
        if workflow.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            raise ValueError("Cannot modify running or paused workflows")

        # Create new step
        step = WorkflowStep(
            id=str(uuid.uuid4()),
            name=step_name,
            step_type=step_type,
            depends_on=depends_on or [],
            parameters=parameters or {},
            condition=condition,
            timeout=timeout,
            max_retries=max_retries,
            task_id=task_id,
            agent_id=agent_id,
            required_tools=required_tools or [],
            integration_id=integration_id,
            integration_method=integration_method,
            integration_endpoint=integration_endpoint,
        )

        # Add step to workflow
        workflow.add_step(step)

        # Validate dependencies
        validation_errors = workflow.validate_dependencies()
        if validation_errors:
            raise ValueError(f"Invalid dependencies: {'; '.join(validation_errors)}")

        # Save updated workflow
        await workflow_repository.save_workflow(workflow)

        logger.info(f"Added step {step.id} to workflow {workflow_id}")
        return workflow

    async def remove_step_from_workflow(
        self, workflow_id: str, step_id: str
    ) -> Optional[Workflow]:
        """Remove a step from a workflow"""
        workflow = await workflow_repository.get_workflow_by_id(workflow_id)
        if not workflow:
            return None

        # Don't allow modification of running workflows
        if workflow.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            raise ValueError("Cannot modify running or paused workflows")

        # Remove step
        if workflow.remove_step(step_id):
            await workflow_repository.save_workflow(workflow)
            logger.info(f"Removed step {step_id} from workflow {workflow_id}")
            return workflow

        return None

    async def execute_workflow(self, workflow_id: str) -> bool:
        """Start executing a workflow"""
        workflow = await workflow_repository.get_workflow_by_id(workflow_id)
        if not workflow:
            return False

        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow {workflow_id} is not in pending status")

        try:
            await self.workflow_engine.execute_workflow(workflow)
            logger.info(f"Started execution of workflow {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {str(e)}")
            return False

    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        return await self.workflow_engine.pause_workflow(workflow_id)

    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        return await self.workflow_engine.resume_workflow(workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow"""
        success = await self.workflow_engine.cancel_workflow(workflow_id)
        if success:
            # Update database status
            workflow = await workflow_repository.get_workflow_by_id(workflow_id)
            if workflow:
                workflow.status = WorkflowStatus.CANCELLED
                await workflow_repository.save_workflow(workflow)
        return success

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        return await workflow_repository.get_workflow_by_id(workflow_id)

    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        created_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Workflow]:
        """List workflows with filtering"""
        return await workflow_repository.list_workflows(
            status=status, created_by=created_by, limit=limit, offset=offset
        )

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        # Cancel if running
        await self.cancel_workflow(workflow_id)

        # Delete from database
        success = await workflow_repository.delete_workflow(workflow_id)
        if success:
            # Emit workflow deleted event
            await self.event_bus.emit(
                WorkflowEvent.workflow_deleted(workflow_id=workflow_id)
            )
            logger.info(f"Deleted workflow {workflow_id}")

        return success

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed workflow status"""
        # Try to get from engine first (for active workflows)
        status = await self.workflow_engine.get_workflow_status(workflow_id)
        if status:
            return status

        # Fallback to database
        workflow = await workflow_repository.get_workflow_by_id(workflow_id)
        if not workflow:
            return None

        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat()
            if workflow.started_at
            else None,
            "completed_at": workflow.completed_at.isoformat()
            if workflow.completed_at
            else None,
            "execution_time": workflow.execution_time,
            "total_steps": len(workflow.steps),
            "completed_steps": len(workflow.completed_step_ids),
            "failed_steps": len(workflow.failed_step_ids),
            "running_steps": len(
                [s for s in workflow.steps.values() if s.status == StepStatus.RUNNING]
            ),
            "error_message": workflow.error_message,
        }

    async def get_workflow_steps(
        self, workflow_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get workflow steps with their status"""
        workflow = await workflow_repository.get_workflow_by_id(workflow_id)
        if not workflow:
            return None

        steps = []
        for step in workflow.steps.values():
            steps.append(
                {
                    "id": step.id,
                    "name": step.name,
                    "step_type": step.step_type.value,
                    "status": step.status.value,
                    "depends_on": step.depends_on,
                    "parameters": step.parameters,
                    "condition": step.condition,
                    "timeout": step.timeout,
                    "retry_count": step.retry_count,
                    "max_retries": step.max_retries,
                    "task_id": step.task_id,
                    "agent_id": step.agent_id,
                    "required_tools": step.required_tools,
                    "integration_id": step.integration_id,
                    "integration_method": step.integration_method,
                    "integration_endpoint": step.integration_endpoint,
                    "results": step.results,
                    "error_message": step.error_message,
                    "started_at": step.started_at.isoformat()
                    if step.started_at
                    else None,
                    "completed_at": step.completed_at.isoformat()
                    if step.completed_at
                    else None,
                    "execution_time": step.execution_time,
                }
            )

        return steps

    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return await self.workflow_engine.list_active_workflows()

    async def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        stats = await workflow_repository.get_workflow_statistics()

        # Add engine statistics
        active_workflows = await self.workflow_engine.list_active_workflows()
        stats["active_workflows"] = len(active_workflows)
        stats["engine_running"] = self.workflow_engine.is_running

        return stats

    async def create_simple_task_workflow(
        self,
        name: str,
        description: str,
        tasks: List[Dict[str, Any]],
        created_by: Optional[str] = None,
    ) -> Workflow:
        """Create a simple workflow with sequential task execution"""
        workflow = await self.create_workflow(
            name=name, description=description, created_by=created_by
        )

        previous_step_id = None
        for i, task_config in enumerate(tasks):
            step_name = task_config.get("name", f"Task {i + 1}")
            depends_on = [previous_step_id] if previous_step_id else []

            await self.add_step_to_workflow(
                workflow_id=workflow.id,
                step_name=step_name,
                step_type=StepType.TASK,
                depends_on=depends_on,
                parameters=task_config.get("parameters", {}),
                agent_id=task_config.get("agent_id"),
                required_tools=task_config.get("required_tools", []),
                timeout=task_config.get("timeout"),
                max_retries=task_config.get("max_retries", 3),
            )

            # Get the step ID of the step we just added
            updated_workflow = await workflow_repository.get_workflow_by_id(workflow.id)
            if updated_workflow:
                # Find the step we just added (last one)
                step_ids = list(updated_workflow.steps.keys())
                previous_step_id = step_ids[-1] if step_ids else None

        return await workflow_repository.get_workflow_by_id(workflow.id) or workflow
