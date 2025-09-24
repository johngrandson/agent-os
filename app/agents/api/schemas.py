"""Agent API schemas - consolidated request/response models"""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Request Models
class CreateAgentRequest(BaseModel):
    """Agent creation request"""

    name: str = Field(..., description="Agent name")
    phone_number: str = Field(..., description="Agent phone number")
    description: str | None = Field(None, description="Agent description")
    instructions: list[str] | None = Field(None, description="Agent instructions")
    is_active: bool = Field(default=False, description="Agent active status")
    whatsapp_enabled: bool = Field(default=False, description="WhatsApp enabled status")
    whatsapp_token: str | None = Field(None, description="WhatsApp token")


class UpdateAgentRequest(BaseModel):
    """Agent update request"""

    name: str = Field(None, description="Agent name")
    phone_number: str = Field(None, description="Agent phone number")
    description: str | None = Field(None, description="Agent description")
    instructions: list[str] | None = Field(None, description="Agent instructions")
    is_active: bool = Field(None, description="Agent active status")
    whatsapp_enabled: bool | None = Field(None, description="WhatsApp enabled status")
    whatsapp_token: str | None = Field(None, description="WhatsApp token")


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
    description: str | None = Field(None, description="Agent description")
    instructions: list[str] | None = Field(None, description="Agent instructions")
    is_active: bool = Field(..., description="Agent active status")

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
    description: str | None = None
    instructions: list[str] | None = None
    is_active: bool


class UpdateAgentCommand(BaseModel):
    """Internal command for agent updates"""

    agent_id: str
    name: str
    phone_number: str
    description: str | None = None
    instructions: list[str] | None = None
    is_active: bool
