"""
Tool domain event classes
"""

from typing import Dict, Any, Optional
from app.events.core import BaseEvent, EventPriority
from .types import ToolEventType


class ToolEvent(BaseEvent):
    """Tool execution events"""

    tool_name: str
    agent_id: Optional[str] = None

    @classmethod
    def tool_executed(
        cls, tool_name: str, agent_id: str = None, results: Dict[str, Any] = None
    ) -> "ToolEvent":
        return cls(
            event_type=ToolEventType.TOOL_EXECUTED,
            tool_name=tool_name,
            agent_id=agent_id,
            data={"results": results or {}},
            source=agent_id or "tool_registry",
        )

    @classmethod
    def tool_failed(
        cls, tool_name: str, agent_id: str = None, error: str = None
    ) -> "ToolEvent":
        return cls(
            event_type=ToolEventType.TOOL_FAILED,
            tool_name=tool_name,
            agent_id=agent_id,
            data={"error": error},
            source=agent_id or "tool_registry",
            priority=EventPriority.HIGH,
        )

    @classmethod
    def tool_registered(
        cls, tool_name: str, data: Dict[str, Any] = None
    ) -> "ToolEvent":
        return cls(
            event_type=ToolEventType.TOOL_REGISTERED,
            tool_name=tool_name,
            data=data or {},
            source="tool_registry",
        )

    @classmethod
    def tool_unregistered(
        cls, tool_name: str, data: Dict[str, Any] = None
    ) -> "ToolEvent":
        return cls(
            event_type=ToolEventType.TOOL_UNREGISTERED,
            tool_name=tool_name,
            data=data or {},
            source="tool_registry",
        )
