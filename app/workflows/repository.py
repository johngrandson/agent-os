"""
Repository for persisting workflows
"""

import uuid
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import session_factory, Base
from app.workflows.workflow import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepStatus,
    StepType,
)


class WorkflowModel(Base):
    """SQLAlchemy model for workflows"""

    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False, default="pending")

    # Workflow structure and metadata
    steps_data = Column(JSON, nullable=False, default=dict)
    workflow_metadata = Column(JSON, nullable=False, default=dict)

    # Execution control
    created_by = Column(String(255))
    timeout = Column(Integer)  # in seconds
    max_parallel_steps = Column(Integer, default=5)
    auto_retry_failed = Column(Boolean, default=True)

    # Execution state
    current_step_ids = Column(JSON, nullable=False, default=list)
    completed_step_ids = Column(JSON, nullable=False, default=list)
    failed_step_ids = Column(JSON, nullable=False, default=list)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time = Column(Integer)  # in seconds

    # Results
    results = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text)


class WorkflowRepository:
    """Repository for workflow persistence"""

    async def save_workflow(self, workflow: Workflow) -> Workflow:
        """Save a workflow to the database"""
        async with session_factory() as session:
            # Check if workflow exists
            existing = await session.get(WorkflowModel, uuid.UUID(workflow.id))

            if existing:
                # Update existing workflow
                existing.name = workflow.name
                existing.description = workflow.description
                existing.status = workflow.status.value
                existing.steps_data = self._serialize_steps(workflow.steps)
                existing.workflow_metadata = workflow.metadata
                existing.created_by = workflow.created_by
                existing.timeout = int(workflow.timeout) if workflow.timeout else None
                existing.max_parallel_steps = workflow.max_parallel_steps
                existing.auto_retry_failed = workflow.auto_retry_failed
                existing.current_step_ids = workflow.current_step_ids
                existing.completed_step_ids = list(workflow.completed_step_ids)
                existing.failed_step_ids = list(workflow.failed_step_ids)
                existing.started_at = workflow.started_at
                existing.completed_at = workflow.completed_at
                existing.execution_time = (
                    int(workflow.execution_time) if workflow.execution_time else None
                )
                existing.results = workflow.results
                existing.error_message = workflow.error_message

                await session.commit()
                await session.refresh(existing)

            else:
                # Create new workflow
                workflow_model = WorkflowModel(
                    id=uuid.UUID(workflow.id),
                    name=workflow.name,
                    description=workflow.description,
                    status=workflow.status.value,
                    steps_data=self._serialize_steps(workflow.steps),
                    workflow_metadata=workflow.metadata,
                    created_by=workflow.created_by,
                    timeout=int(workflow.timeout) if workflow.timeout else None,
                    max_parallel_steps=workflow.max_parallel_steps,
                    auto_retry_failed=workflow.auto_retry_failed,
                    current_step_ids=workflow.current_step_ids,
                    completed_step_ids=list(workflow.completed_step_ids),
                    failed_step_ids=list(workflow.failed_step_ids),
                    created_at=workflow.created_at,
                    started_at=workflow.started_at,
                    completed_at=workflow.completed_at,
                    execution_time=int(workflow.execution_time)
                    if workflow.execution_time
                    else None,
                    results=workflow.results,
                    error_message=workflow.error_message,
                )

                session.add(workflow_model)
                await session.commit()
                await session.refresh(workflow_model)

            return workflow

    async def get_workflow_by_id(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        async with session_factory() as session:
            workflow_model = await session.get(WorkflowModel, uuid.UUID(workflow_id))
            if workflow_model:
                return self._model_to_workflow(workflow_model)
            return None

    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        created_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Workflow]:
        """List workflows with optional filtering"""
        from sqlalchemy import select

        async with session_factory() as session:
            query = select(WorkflowModel)

            if status:
                query = query.where(WorkflowModel.status == status.value)
            if created_by:
                query = query.where(WorkflowModel.created_by == created_by)

            query = query.order_by(WorkflowModel.created_at.desc())
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            workflow_models = result.scalars().all()

            return [self._model_to_workflow(model) for model in workflow_models]

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        async with session_factory() as session:
            workflow_model = await session.get(WorkflowModel, uuid.UUID(workflow_id))
            if workflow_model:
                await session.delete(workflow_model)
                await session.commit()
                return True
            return False

    async def get_active_workflows(self) -> List[Workflow]:
        """Get all active (running/paused) workflows"""
        from sqlalchemy import select

        async with session_factory() as session:
            query = select(WorkflowModel).where(
                WorkflowModel.status.in_(["running", "paused"])
            )
            result = await session.execute(query)
            workflow_models = result.scalars().all()

            return [self._model_to_workflow(model) for model in workflow_models]

    async def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        from sqlalchemy import select, func

        async with session_factory() as session:
            # Count by status
            query = select(
                WorkflowModel.status, func.count(WorkflowModel.id).label("count")
            ).group_by(WorkflowModel.status)

            result = await session.execute(query)
            status_counts = {row.status: row.count for row in result}

            # Total count
            total_query = select(func.count(WorkflowModel.id))
            total_result = await session.execute(total_query)
            total_count = total_result.scalar()

            # Average execution time for completed workflows
            avg_time_query = select(func.avg(WorkflowModel.execution_time)).where(
                WorkflowModel.status == "completed"
            )

            avg_time_result = await session.execute(avg_time_query)
            avg_execution_time = avg_time_result.scalar()

            return {
                "total_workflows": total_count,
                "by_status": status_counts,
                "average_execution_time": float(avg_execution_time)
                if avg_execution_time
                else None,
            }

    def _serialize_steps(self, steps: Dict[str, WorkflowStep]) -> Dict[str, Any]:
        """Serialize workflow steps to JSON-compatible format"""
        serialized = {}
        for step_id, step in steps.items():
            serialized[step_id] = {
                "id": step.id,
                "name": step.name,
                "step_type": step.step_type.value,
                "status": step.status.value,
                "depends_on": step.depends_on,
                "condition": step.condition,
                "parameters": step.parameters,
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
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat()
                if step.completed_at
                else None,
                "execution_time": step.execution_time,
            }
        return serialized

    def _deserialize_steps(self, steps_data: Dict[str, Any]) -> Dict[str, WorkflowStep]:
        """Deserialize workflow steps from JSON format"""
        steps = {}
        for step_id, step_data in steps_data.items():
            step = WorkflowStep(
                id=step_data["id"],
                name=step_data["name"],
                step_type=StepType(step_data["step_type"]),
                status=StepStatus(step_data["status"]),
                depends_on=step_data.get("depends_on", []),
                condition=step_data.get("condition"),
                parameters=step_data.get("parameters", {}),
                timeout=step_data.get("timeout"),
                retry_count=step_data.get("retry_count", 0),
                max_retries=step_data.get("max_retries", 3),
                task_id=step_data.get("task_id"),
                agent_id=step_data.get("agent_id"),
                required_tools=step_data.get("required_tools", []),
                integration_id=step_data.get("integration_id"),
                integration_method=step_data.get("integration_method"),
                integration_endpoint=step_data.get("integration_endpoint"),
                results=step_data.get("results"),
                error_message=step_data.get("error_message"),
                started_at=datetime.fromisoformat(step_data["started_at"])
                if step_data.get("started_at")
                else None,
                completed_at=datetime.fromisoformat(step_data["completed_at"])
                if step_data.get("completed_at")
                else None,
                execution_time=step_data.get("execution_time"),
            )
            steps[step_id] = step
        return steps

    def _model_to_workflow(self, model: WorkflowModel) -> Workflow:
        """Convert database model to workflow object"""
        workflow = Workflow(
            id=str(model.id),
            name=model.name,
            description=model.description,
            status=WorkflowStatus(model.status),
            steps=self._deserialize_steps(model.steps_data),
            metadata=model.workflow_metadata,
            created_by=model.created_by,
            timeout=float(model.timeout) if model.timeout else None,
            max_parallel_steps=model.max_parallel_steps,
            auto_retry_failed=model.auto_retry_failed,
            current_step_ids=model.current_step_ids,
            completed_step_ids=set(model.completed_step_ids),
            failed_step_ids=set(model.failed_step_ids),
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            execution_time=float(model.execution_time)
            if model.execution_time
            else None,
            results=model.results,
            error_message=model.error_message,
        )
        return workflow


# Repository instance
workflow_repository = WorkflowRepository()
