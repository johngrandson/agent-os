"""
API schemas for tool management
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.tools.base import ToolStatus


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool"""

    tool_name: str
    parameters: Dict[str, Any]
    timeout: Optional[float] = None


class ToolExecutionResponse(BaseModel):
    """Response from tool execution"""

    tool_name: str
    status: ToolStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ToolDefinitionResponse(BaseModel):
    """Tool definition response"""

    name: str
    description: str
    category: str
    definition: Dict[str, Any]


class ToolListResponse(BaseModel):
    """Response with list of available tools"""

    tools: List[ToolDefinitionResponse]
    total_count: int
