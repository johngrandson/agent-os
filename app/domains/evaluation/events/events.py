"""Evaluation domain events"""

from dataclasses import dataclass
from typing import Any

from app.shared.events.base import BaseEvent
from typing_extensions import TypedDict


class EvalEventPayload(TypedDict):
    """Type for evaluation event payloads received by handlers"""

    entity_id: str
    event_type: str
    data: dict[str, Any]


@dataclass
class EvalEvent(BaseEvent):
    """Evaluation-specific event"""

    @classmethod
    def failed(cls, agent_id: str, eval_data: dict[str, Any]) -> "EvalEvent":
        """Create evaluation failed event"""
        return cls(entity_id=agent_id, event_type="failed", data=eval_data)
