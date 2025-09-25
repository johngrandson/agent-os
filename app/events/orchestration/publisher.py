"""Orchestration event publisher"""

from typing import Any

from app.events.core.base import BaseEventPublisher

from .events import OrchestrationEvent


class OrchestrationEventPublisher(BaseEventPublisher):
    """Publisher for orchestration domain events"""

    def get_domain_prefix(self) -> str:
        return "orchestration"

    async def task_created(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Publish task created event"""
        event = OrchestrationEvent.task_created(task_id, task_data)
        await self.publish_domain_event("task_created", event)

    async def task_completed(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Publish task completed event"""
        event = OrchestrationEvent.task_completed(task_id, task_data)
        await self.publish_domain_event("task_completed", event)

    async def task_failed(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Publish task failed event"""
        event = OrchestrationEvent.task_failed(task_id, task_data)
        await self.publish_domain_event("task_failed", event)

    # Backwards compatibility methods (can be removed later)
    async def publish_task_created(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Backward compatibility alias for task_created"""
        await self.task_created(task_id, task_data)

    async def publish_task_completed(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Backward compatibility alias for task_completed"""
        await self.task_completed(task_id, task_data)

    async def publish_task_failed(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Backward compatibility alias for task_failed"""
        await self.task_failed(task_id, task_data)
