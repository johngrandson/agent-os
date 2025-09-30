"""Evaluation event publisher"""

from typing import Any

from app.shared.events.base import BaseEventPublisher

from .events import EvalEvent


class EvaluationEventPublisher(BaseEventPublisher):
    """Publisher for evaluation domain events"""

    def get_domain_prefix(self) -> str:
        return "evaluation"

    async def eval_failed(self, agent_id: str, eval_data: dict[str, Any]) -> None:
        """Publish evaluation failed event"""
        event = EvalEvent.failed(agent_id, eval_data)
        await self.publish_domain_event("failed", event)
