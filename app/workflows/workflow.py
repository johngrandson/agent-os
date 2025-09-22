"""
Workflow models for multi-agent orchestration
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field


class WorkflowStatus(Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Workflow step execution status"""

    PENDING = "pending"
    READY = "ready"  # Dependencies satisfied
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(Enum):
    """Types of workflow steps"""

    TASK = "task"  # Execute a task
    CONDITION = "condition"  # Conditional branch
    PARALLEL = "parallel"  # Parallel execution group
    WAIT = "wait"  # Wait/delay step
    NOTIFICATION = "notification"  # Send notification
    INTEGRATION = "integration"  # External integration call


@dataclass
class WorkflowStep:
    """Individual step in a workflow"""

    id: str
    name: str
    step_type: StepType
    status: StepStatus = StepStatus.PENDING

    # Dependencies and flow control
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    condition: Optional[str] = None  # Condition expression for conditional steps

    # Execution parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

    # Task/Agent assignment
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    required_tools: List[str] = field(default_factory=list)

    # Integration parameters
    integration_id: Optional[str] = None
    integration_method: Optional[str] = None
    integration_endpoint: Optional[str] = None

    # Results and execution info
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None

    def start_execution(self):
        """Mark step as started"""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_execution(self, results: Dict[str, Any]):
        """Mark step as completed with results"""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.results = results
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def fail_execution(self, error_message: str):
        """Mark step as failed"""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def skip_execution(self, reason: str):
        """Skip step execution"""
        self.status = StepStatus.SKIPPED
        self.completed_at = datetime.utcnow()
        self.error_message = f"Skipped: {reason}"

    def can_execute(self, completed_steps: set) -> bool:
        """Check if step dependencies are satisfied"""
        return all(dep_id in completed_steps for dep_id in self.depends_on)


@dataclass
class Workflow:
    """Workflow definition and execution state"""

    id: str
    name: str
    description: str
    status: WorkflowStatus = WorkflowStatus.PENDING

    # Workflow structure
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Execution control
    created_by: Optional[str] = None
    timeout: Optional[float] = None
    max_parallel_steps: int = 5
    auto_retry_failed: bool = True

    # Execution state
    current_step_ids: List[str] = field(default_factory=list)  # Currently executing
    completed_step_ids: set = field(default_factory=set)
    failed_step_ids: set = field(default_factory=set)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None

    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    @classmethod
    def create(
        cls, name: str, description: str, created_by: Optional[str] = None
    ) -> "Workflow":
        """Create a new workflow"""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_by=created_by,
        )

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        self.steps[step.id] = step

    def remove_step(self, step_id: str) -> bool:
        """Remove a step from the workflow"""
        if step_id in self.steps:
            # Remove dependencies on this step from other steps
            for step in self.steps.values():
                if step_id in step.depends_on:
                    step.depends_on.remove(step_id)

            del self.steps[step_id]
            return True
        return False

    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute"""
        ready_steps = []
        for step in self.steps.values():
            if step.status == StepStatus.PENDING and step.can_execute(
                self.completed_step_ids
            ):
                step.status = StepStatus.READY
                ready_steps.append(step)
        return ready_steps

    def get_running_steps(self) -> List[WorkflowStep]:
        """Get currently running steps"""
        return [
            step for step in self.steps.values() if step.status == StepStatus.RUNNING
        ]

    def start_execution(self):
        """Start workflow execution"""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_execution(self):
        """Complete workflow execution"""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

        # Collect results from all steps
        self.results = {
            "completed_steps": len(self.completed_step_ids),
            "failed_steps": len(self.failed_step_ids),
            "step_results": {
                step_id: step.results
                for step_id, step in self.steps.items()
                if step.results is not None
            },
        }

    def fail_execution(self, error_message: str):
        """Fail workflow execution"""
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def pause_execution(self):
        """Pause workflow execution"""
        self.status = WorkflowStatus.PAUSED

    def resume_execution(self):
        """Resume workflow execution"""
        if self.status == WorkflowStatus.PAUSED:
            self.status = WorkflowStatus.RUNNING

    def cancel_execution(self):
        """Cancel workflow execution"""
        self.status = WorkflowStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def is_completed(self) -> bool:
        """Check if workflow is completed"""
        if not self.steps:
            return True

        total_steps = len(self.steps)
        finished_steps = len(self.completed_step_ids) + len(self.failed_step_ids)
        return finished_steps == total_steps

    def has_failed_critical_steps(self) -> bool:
        """Check if workflow has failed critical steps that should stop execution"""
        for step_id in self.failed_step_ids:
            step = self.steps.get(step_id)
            if step and step.retry_count >= step.max_retries:
                return True
        return False

    def get_step_dependency_graph(self) -> Dict[str, List[str]]:
        """Get dependency graph for visualization"""
        graph = {}
        for step_id, step in self.steps.items():
            graph[step_id] = step.depends_on.copy()
        return graph

    def validate_dependencies(self) -> List[str]:
        """Validate workflow dependencies and return any errors"""
        errors = []

        # Check for circular dependencies
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = self.steps.get(step_id)
            if step:
                for dep_id in step.depends_on:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(step_id)
            return False

        for step_id in self.steps:
            if step_id not in visited:
                if has_cycle(step_id):
                    errors.append(
                        f"Circular dependency detected involving step {step_id}"
                    )

        # Check for invalid dependencies
        for step_id, step in self.steps.items():
            for dep_id in step.depends_on:
                if dep_id not in self.steps:
                    errors.append(
                        f"Step {step_id} depends on non-existent step {dep_id}"
                    )

        return errors
