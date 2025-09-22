"""
Base classes for the agent tool framework
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum


class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ToolResult(BaseModel):
    """Result from tool execution"""

    status: ToolStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ToolParameter(BaseModel):
    """Definition of a tool parameter"""

    name: str
    type: str  # "string", "number", "boolean", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Tool metadata and configuration"""

    name: str
    description: str
    parameters: list[ToolParameter]
    category: str = "general"
    version: str = "1.0"


class AgentTool(ABC):
    """Abstract base class for all agent tools"""

    def __init__(self, name: str, description: str, category: str = "general"):
        self.name = name
        self.description = description
        self.category = category

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters"""
        pass

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Get tool definition with parameters"""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters against tool definition"""
        definition = self.get_definition()

        for param in definition.parameters:
            if param.required and param.name not in parameters:
                return False

        return True
