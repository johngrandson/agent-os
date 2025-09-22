"""
Workflow execution engine for orchestrating multi-agent tasks
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.workflows.workflow import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepStatus,
    StepType,
)
from app.events.bus import EventBus
from app.workflows.events import WorkflowEvent
from app.tasks.services.task_service import TaskService
from app.integrations.services import IntegrationService
from app.agents.services.agent_service import AgentService

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Engine for executing workflows with multi-agent orchestration"""

    def __init__(
        self,
        event_bus: EventBus,
        task_service: TaskService,
        integration_service: IntegrationService,
        agent_service: AgentService,
    ):
        self.event_bus = event_bus
        self.task_service = task_service
        self.integration_service = integration_service
        self.agent_service = agent_service

        # Active workflows
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_tasks: Dict[str, asyncio.Task] = {}

        # Engine state
        self.is_running = False
        self.max_concurrent_workflows = 10

    async def start(self):
        """Start the workflow engine"""
        self.is_running = True
        logger.info("Workflow engine started")

        # Emit engine started event
        await self.event_bus.emit(
            WorkflowEvent.engine_started(
                data={"max_concurrent": self.max_concurrent_workflows}
            )
        )

    async def stop(self):
        """Stop the workflow engine"""
        self.is_running = False

        # Cancel all running workflow tasks
        for workflow_id, task in self.workflow_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled workflow {workflow_id}")

        # Wait for all tasks to complete
        if self.workflow_tasks:
            await asyncio.gather(*self.workflow_tasks.values(), return_exceptions=True)

        self.workflow_tasks.clear()
        self.active_workflows.clear()

        logger.info("Workflow engine stopped")

        # Emit engine stopped event
        await self.event_bus.emit(WorkflowEvent.engine_stopped())

    async def execute_workflow(self, workflow: Workflow) -> None:
        """Execute a workflow asynchronously"""
        if not self.is_running:
            raise RuntimeError("Workflow engine is not running")

        if len(self.active_workflows) >= self.max_concurrent_workflows:
            raise RuntimeError("Maximum concurrent workflows exceeded")

        # Validate workflow
        validation_errors = workflow.validate_dependencies()
        if validation_errors:
            raise ValueError(
                f"Workflow validation failed: {'; '.join(validation_errors)}"
            )

        # Add to active workflows
        self.active_workflows[workflow.id] = workflow

        # Create and start execution task
        workflow_task = asyncio.create_task(self._execute_workflow_async(workflow))
        self.workflow_tasks[workflow.id] = workflow_task

        logger.info(f"Started execution of workflow {workflow.id}: {workflow.name}")

    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.RUNNING:
            return False

        workflow.pause_execution()
        logger.info(f"Paused workflow {workflow_id}")

        # Emit workflow paused event
        await self.event_bus.emit(
            WorkflowEvent.workflow_paused(workflow_id=workflow_id)
        )

        return True

    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.PAUSED:
            return False

        workflow.resume_execution()
        logger.info(f"Resumed workflow {workflow_id}")

        # Emit workflow resumed event
        await self.event_bus.emit(
            WorkflowEvent.workflow_resumed(workflow_id=workflow_id)
        )

        return True

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.cancel_execution()

        # Cancel the execution task
        workflow_task = self.workflow_tasks.get(workflow_id)
        if workflow_task and not workflow_task.done():
            workflow_task.cancel()

        # Remove from active workflows
        self.active_workflows.pop(workflow_id, None)
        self.workflow_tasks.pop(workflow_id, None)

        logger.info(f"Cancelled workflow {workflow_id}")

        # Emit workflow cancelled event
        await self.event_bus.emit(
            WorkflowEvent.workflow_cancelled(workflow_id=workflow_id)
        )

        return True

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow"""
        workflow = self.active_workflows.get(workflow_id)
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
            "running_steps": len(workflow.get_running_steps()),
            "error_message": workflow.error_message,
        }

    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        workflows = []
        for workflow in self.active_workflows.values():
            status = await self.get_workflow_status(workflow.id)
            if status:
                workflows.append(status)
        return workflows

    async def _execute_workflow_async(self, workflow: Workflow) -> None:
        """Execute a workflow asynchronously"""
        try:
            # Start workflow
            workflow.start_execution()
            await self.event_bus.emit(
                WorkflowEvent.workflow_started(
                    workflow_id=workflow.id,
                    data={"name": workflow.name, "total_steps": len(workflow.steps)},
                )
            )

            logger.info(f"Executing workflow {workflow.id}: {workflow.name}")

            # Main execution loop
            while workflow.status == WorkflowStatus.RUNNING:
                # Check if workflow is completed
                if workflow.is_completed():
                    workflow.complete_execution()
                    break

                # Check for critical failures
                if workflow.has_failed_critical_steps():
                    workflow.fail_execution("Critical step failures detected")
                    break

                # Get ready steps
                ready_steps = workflow.get_ready_steps()
                running_steps = workflow.get_running_steps()

                # Start new steps if we have capacity
                available_slots = workflow.max_parallel_steps - len(running_steps)
                steps_to_start = ready_steps[:available_slots]

                for step in steps_to_start:
                    await self._execute_step(workflow, step)

                # Wait briefly before next iteration
                await asyncio.sleep(0.1)

                # Handle paused state
                while workflow.status == WorkflowStatus.PAUSED:
                    await asyncio.sleep(1.0)

            # Finalize workflow
            await self._finalize_workflow(workflow)

        except asyncio.CancelledError:
            workflow.cancel_execution()
            await self._finalize_workflow(workflow)
            raise

        except Exception as e:
            logger.error(f"Workflow {workflow.id} execution failed: {str(e)}")
            workflow.fail_execution(str(e))
            await self._finalize_workflow(workflow)

    async def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a workflow step"""
        step.start_execution()

        # Emit step started event
        await self.event_bus.emit(
            WorkflowEvent.step_started(
                workflow_id=workflow.id,
                step_id=step.id,
                data={"step_name": step.name, "step_type": step.step_type.value},
            )
        )

        logger.info(
            f"Executing step {step.id}: {step.name} (type: {step.step_type.value})"
        )

        try:
            # Execute based on step type
            if step.step_type == StepType.TASK:
                await self._execute_task_step(workflow, step)
            elif step.step_type == StepType.INTEGRATION:
                await self._execute_integration_step(workflow, step)
            elif step.step_type == StepType.NOTIFICATION:
                await self._execute_notification_step(workflow, step)
            elif step.step_type == StepType.WAIT:
                await self._execute_wait_step(workflow, step)
            elif step.step_type == StepType.CONDITION:
                await self._execute_condition_step(workflow, step)
            else:
                raise ValueError(f"Unsupported step type: {step.step_type}")

            # Mark as completed
            workflow.completed_step_ids.add(step.id)

            # Emit step completed event
            await self.event_bus.emit(
                WorkflowEvent.step_completed(
                    workflow_id=workflow.id,
                    step_id=step.id,
                    data={"results": step.results},
                )
            )

            logger.info(f"Completed step {step.id}: {step.name}")

        except Exception as e:
            # Handle step failure
            error_message = str(e)
            step.fail_execution(error_message)
            workflow.failed_step_ids.add(step.id)

            # Emit step failed event
            await self.event_bus.emit(
                WorkflowEvent.step_failed(
                    workflow_id=workflow.id,
                    step_id=step.id,
                    data={"error": error_message, "retry_count": step.retry_count},
                )
            )

            logger.error(f"Step {step.id} failed: {error_message}")

            # Retry logic
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                step.status = StepStatus.PENDING
                workflow.failed_step_ids.discard(step.id)
                logger.info(f"Retrying step {step.id} (attempt {step.retry_count + 1})")

    async def _execute_task_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a task step"""
        if not step.task_id and not step.agent_id:
            raise ValueError("Task step requires either task_id or agent_id")

        # Execute existing task or create new one
        if step.task_id:
            result = await self.task_service.execute_task(
                task_id=step.task_id,
                agent_id=step.agent_id,
                parameters=step.parameters,
                timeout=step.timeout,
            )
        else:
            # Create and execute new task
            from app.tasks.api.schemas import CreateTaskCommand
            from app.tasks.task import TaskType, TaskPriority

            task_command = CreateTaskCommand(
                title=step.name,
                description=f"Task created by workflow {workflow.id}",
                task_type=TaskType.AUTOMATION,
                priority=TaskPriority.MEDIUM,
                assigned_agent_id=step.agent_id,
                assigned_by=f"workflow_{workflow.id}",
                parameters=step.parameters,
                expected_tools=step.required_tools,
            )

            task = await self.task_service.create_task(command=task_command)
            result = await self.task_service.execute_task(
                task_id=str(task.id),
                parameters=step.parameters,
                timeout=step.timeout,
            )

        if "error" in result:
            raise Exception(result["error"])

        step.complete_execution(result)

    async def _execute_integration_step(
        self, workflow: Workflow, step: WorkflowStep
    ) -> None:
        """Execute an integration step"""
        if (
            not step.integration_id
            or not step.integration_method
            or not step.integration_endpoint
        ):
            raise ValueError(
                "Integration step requires integration_id, method, and endpoint"
            )

        result = await self.integration_service.execute_integration_request(
            integration_id=uuid.UUID(step.integration_id),
            method=step.integration_method,
            endpoint=step.integration_endpoint,
            data=step.parameters.get("data"),
            headers=step.parameters.get("headers"),
            params=step.parameters.get("params"),
            triggered_by=f"workflow_{workflow.id}",
        )

        if not result.success:
            raise Exception(result.error or "Integration request failed")

        step.complete_execution(
            {
                "status_code": result.status_code,
                "data": result.data,
                "headers": result.headers,
                "execution_time": result.execution_time,
            }
        )

    async def _execute_notification_step(
        self, workflow: Workflow, step: WorkflowStep
    ) -> None:
        """Execute a notification step"""
        # Emit notification event
        await self.event_bus.emit(
            WorkflowEvent.notification_sent(
                workflow_id=workflow.id,
                data={
                    "message": step.parameters.get(
                        "message", f"Notification from workflow {workflow.name}"
                    ),
                    "recipient": step.parameters.get("recipient"),
                    "channel": step.parameters.get("channel", "system"),
                },
            )
        )

        step.complete_execution({"notification_sent": True})

    async def _execute_wait_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a wait step"""
        wait_time = step.parameters.get("seconds", 1.0)
        await asyncio.sleep(wait_time)
        step.complete_execution({"waited_seconds": wait_time})

    async def _execute_condition_step(
        self, workflow: Workflow, step: WorkflowStep
    ) -> None:
        """Execute a condition step"""
        # Simple condition evaluation (can be expanded)
        condition = step.condition or "true"
        context = {
            "workflow": workflow,
            "step_results": {
                step_id: step.results
                for step_id, step in workflow.steps.items()
                if step.results is not None
            },
        }

        # Basic condition evaluation (in production, use a proper expression evaluator)
        try:
            result = eval(condition, {"__builtins__": {}}, context)
            step.complete_execution({"condition_result": bool(result)})
        except Exception as e:
            raise Exception(f"Condition evaluation failed: {str(e)}")

    async def _finalize_workflow(self, workflow: Workflow) -> None:
        """Finalize workflow execution"""
        # Remove from active workflows
        self.active_workflows.pop(workflow.id, None)
        self.workflow_tasks.pop(workflow.id, None)

        # Emit workflow completed/failed event
        if workflow.status == WorkflowStatus.COMPLETED:
            await self.event_bus.emit(
                WorkflowEvent.workflow_completed(
                    workflow_id=workflow.id,
                    data={
                        "execution_time": workflow.execution_time,
                        "completed_steps": len(workflow.completed_step_ids),
                        "failed_steps": len(workflow.failed_step_ids),
                    },
                )
            )
        elif workflow.status == WorkflowStatus.FAILED:
            await self.event_bus.emit(
                WorkflowEvent.workflow_failed(
                    workflow_id=workflow.id,
                    data={
                        "error": workflow.error_message,
                        "execution_time": workflow.execution_time,
                        "completed_steps": len(workflow.completed_step_ids),
                        "failed_steps": len(workflow.failed_step_ids),
                    },
                )
            )
        elif workflow.status == WorkflowStatus.CANCELLED:
            await self.event_bus.emit(
                WorkflowEvent.workflow_cancelled(workflow_id=workflow.id)
            )

        logger.info(
            f"Workflow {workflow.id} finalized with status {workflow.status.value}"
        )
