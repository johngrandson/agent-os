"""Task registry for in-memory task state management"""

from collections import defaultdict

from app.events.orchestration.task_state import TaskState, TaskStatus
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class TaskRegistry:
    """In-memory registry for task state management with dependency resolution"""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._dependencies_graph: dict[str, set[str]] = defaultdict(set)  # task_id -> dependents
        self._completed_tasks: set[str] = set()
        self.logger = get_module_logger(f"{__name__}.{self.__class__.__name__}")

    def create_task(
        self,
        task_id: str | None = None,
        agent_id: str | None = None,
        task_type: str = "",
        dependencies: set[str] | None = None,
        data: dict | None = None,
    ) -> TaskState:
        """Create a new task in the registry"""
        if dependencies is None:
            dependencies = set()
        if data is None:
            data = {}

        task = TaskState(
            task_id=task_id or TaskState().task_id,
            agent_id=agent_id,
            task_type=task_type,
            dependencies=dependencies.copy(),
            data=data.copy(),
        )

        self._tasks[task.task_id] = task

        # Update dependency graph
        for dep_id in dependencies:
            self._dependencies_graph[dep_id].add(task.task_id)

        # Check if task can be marked as ready
        self._update_task_readiness(task.task_id)

        self.logger.info(f"Created task {task.task_id} with dependencies: {dependencies}")
        return task

    def get_task(self, task_id: str) -> TaskState | None:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def update_task_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        result: dict | None = None,
        error: str | None = None,
    ) -> bool:
        """Update task status with validation and optional result/error"""
        task = self._tasks.get(task_id)
        if not task:
            self.logger.warning(f"Task {task_id} not found")
            return False

        old_status = task.status
        task.update_status(new_status)

        # Set result or error if provided
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error

        # Handle completion
        if new_status == TaskStatus.COMPLETED:
            self._completed_tasks.add(task_id)
            self._update_dependent_tasks_readiness(task_id)
        elif new_status == TaskStatus.FAILED:
            self._completed_tasks.discard(task_id)

        self.logger.info(f"Updated task {task_id} status: {old_status.value} -> {new_status.value}")
        return True

    def get_ready_tasks(self) -> list[TaskState]:
        """Get all tasks that are ready to be started"""
        return [task for task in self._tasks.values() if task.status == TaskStatus.READY]

    def get_tasks_by_status(self, status: TaskStatus) -> list[TaskState]:
        """Get all tasks with a specific status"""
        return [task for task in self._tasks.values() if task.status == status]

    def clear(self) -> None:
        """Clear all tasks and reset registry state"""
        self._tasks.clear()
        self._dependencies_graph.clear()
        self._completed_tasks.clear()
        self.logger.info("Cleared all tasks from registry")

    def _update_task_readiness(self, task_id: str) -> None:
        """Update a single task's readiness status"""
        task = self._tasks.get(task_id)
        if not task:
            return

        # Only update if task is in PENDING status and becomes ready
        if task.status == TaskStatus.PENDING and task.is_ready(self._completed_tasks):
            task.update_status(TaskStatus.READY)

    def _update_dependent_tasks_readiness(self, completed_task_id: str) -> None:
        """Update readiness for all tasks that depend on the completed task"""
        dependent_tasks = self._dependencies_graph.get(completed_task_id, set())
        for dependent_id in dependent_tasks:
            self._update_task_readiness(dependent_id)
