"""Orchestration event handlers"""

from app.events.core.registry import event_registry
from app.events.orchestration.task_registry import TaskRegistry
from app.events.orchestration.task_state import TaskStatus
from core.logger import get_module_logger
from faststream.redis import RedisRouter


logger = get_module_logger(__name__)

# Create orchestration-specific router
orchestration_router = RedisRouter()

# Global task registry for handler state management
task_registry = TaskRegistry()


@orchestration_router.subscriber("orchestration.task_created")
async def handle_task_created(data: dict):
    """Handle task created events"""
    entity_id = data.get("entity_id")
    task_data = data.get("data", {})

    logger.info(f"Task created: {entity_id}")
    logger.debug(f"Task data: {task_data}")

    # Create task in registry if not already present
    if entity_id and not task_registry.get_task(entity_id):
        task_registry.create_task(
            task_id=entity_id,
            agent_id=task_data.get("agent_id"),
            task_type=task_data.get("task_type", ""),
            dependencies=set(task_data.get("dependencies", [])),
            data=task_data.get("data", {}),
        )


@orchestration_router.subscriber("orchestration.task_completed")
async def handle_task_completed(data: dict):
    """Handle task completed events"""
    entity_id = data.get("entity_id")
    task_data = data.get("data", {})

    logger.info(f"Task completed: {entity_id}")
    logger.debug(f"Task data: {task_data}")

    # Update task state in registry
    if entity_id:
        task_registry.update_task_status(
            entity_id, TaskStatus.COMPLETED, result=task_data.get("result")
        )


@orchestration_router.subscriber("orchestration.task_failed")
async def handle_task_failed(data: dict):
    """Handle task failed events"""
    entity_id = data.get("entity_id")
    task_data = data.get("data", {})
    error_msg = task_data.get("error", "Unknown error")

    logger.error(f"Task failed: {entity_id} - {error_msg}")
    logger.debug(f"Task data: {task_data}")

    # Update task state in registry
    if entity_id:
        task_registry.update_task_status(entity_id, TaskStatus.FAILED, error=error_msg)


# Register the router with the event registry
event_registry.register_domain_router("orchestration", orchestration_router)
