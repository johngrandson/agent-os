"""
Tool event types
"""

from enum import Enum


class ToolEventType(str, Enum):
    """Types of tool-related events"""

    TOOL_REGISTERED = "tool.registered"
    TOOL_UNREGISTERED = "tool.unregistered"
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"
