"""Agent API schemas - consolidated request/response models"""

import uuid
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Request Models
class CreateAgentRequest(BaseModel):
    """Agent creation request"""

    name: str = Field(..., description="Agent name")
    phone_number: str = Field(..., description="Agent phone number")
    description: Optional[str] = Field(None, description="Agent description")
    instructions: Optional[List[str]] = Field(None, description="Agent instructions")
    is_active: bool = Field(default=False, description="Agent active status")
    available_tools: Optional[List[str]] = Field(None, description="Available tools")
    tool_configurations: Optional[Dict[str, Any]] = Field(
        None, description="Tool configurations"
    )


class UpdateAgentRequest(BaseModel):
    """Agent update request"""

    name: str = Field(None, description="Agent name")
    phone_number: str = Field(None, description="Agent phone number")
    description: Optional[str] = Field(None, description="Agent description")
    instructions: Optional[List[str]] = Field(None, description="Agent instructions")
    is_active: bool = Field(None, description="Agent active status")
    available_tools: Optional[List[str]] = Field(None, description="Available tools")
    tool_configurations: Optional[Dict[str, Any]] = Field(
        None, description="Tool configurations"
    )


# Related Entity Schemas
class PromptResponse(BaseModel):
    """Prompt data response"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Prompt ID")
    agent_id: str = Field(..., description="Agent ID")
    prompt_text: str = Field(..., description="Prompt text")
    is_active: bool = Field(..., description="Is active")

    @field_validator("agent_id", mode="before")
    @classmethod
    def validate_agent_id(cls, v):
        """Convert UUID to string"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


# Response Models
class AgentResponse(BaseModel):
    """Agent data response"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    phone_number: str = Field(..., description="Agent phone number")
    description: Optional[str] = Field(None, description="Agent description")
    instructions: Optional[List[str]] = Field(None, description="Agent instructions")
    is_active: bool = Field(..., description="Agent active status")
    available_tools: Optional[List[str]] = Field(None, description="Available tools")
    tool_configurations: Optional[Dict[str, Any]] = Field(
        None, description="Tool configurations"
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v):
        """Convert UUID to string"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class CreateAgentResponse(BaseModel):
    """Agent creation response"""

    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    phone_number: str = Field(..., description="Agent phone number")

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v):
        """Convert UUID to string"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


# Command Models (for internal use)
class CreateAgentCommand(BaseModel):
    """Internal command for agent creation"""

    name: str
    phone_number: str
    description: Optional[str] = None
    instructions: Optional[List[str]] = None
    is_active: bool
    available_tools: Optional[List[str]] = None
    tool_configurations: Optional[Dict[str, Any]] = None


class UpdateAgentCommand(BaseModel):
    """Internal command for agent updates"""

    agent_id: str
    name: str
    phone_number: str
    description: Optional[str] = None
    instructions: Optional[List[str]] = None
    is_active: bool
    available_tools: Optional[List[str]] = None
    tool_configurations: Optional[Dict[str, Any]] = None


# New schemas for agent capabilities and tool execution
class AgentCapabilitiesResponse(BaseModel):
    """Agent capabilities response"""

    agent_id: str
    name: str
    available_tools: List[str] = []
    tool_definitions: List[Dict[str, Any]] = []
    tool_configurations: Dict[str, Any] = {}


class AgentToolExecutionRequest(BaseModel):
    """Request to execute a tool for an agent"""

    tool_name: str
    parameters: Dict[str, Any]
    timeout: Optional[float] = None


class AgentToolExecutionResponse(BaseModel):
    """Response from agent tool execution"""

    agent_id: str
    tool_name: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
