from __future__ import annotations

import uuid

from infrastructure.database import Base
from infrastructure.database.mixins import TimestampMixin
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    instructions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)

    # Tool configuration fields
    available_tools: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    tool_configurations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Knowledge configuration field
    knowledge_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # WhatsApp integration fields
    whatsapp_enabled: Mapped[bool] = mapped_column(default=False)
    whatsapp_token: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        phone_number: str,
        description: str | None = None,
        instructions: list[str] | None = None,
        is_active: bool,
        available_tools: list[str] | None = None,
        tool_configurations: dict | None = None,
        knowledge_config: dict | None = None,
        whatsapp_enabled: bool = False,
        whatsapp_token: str | None = None,
    ) -> Agent:
        return cls(
            name=name,
            phone_number=phone_number,
            description=description,
            instructions=instructions,
            is_active=is_active,
            available_tools=available_tools,
            tool_configurations=tool_configurations,
            knowledge_config=knowledge_config,
            whatsapp_enabled=whatsapp_enabled,
            whatsapp_token=whatsapp_token,
        )


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., title="Agent ID")
    name: str = Field(..., title="Name")
    phone_number: str = Field(..., title="Phone Number")
    description: str | None = Field(None, title="Description")
    is_active: bool = Field(..., title="Is Active")
    available_tools: list[str] | None = Field(None, title="Available Tools")
    tool_configurations: dict | None = Field(None, title="Tool Configurations")
    knowledge_config: dict | None = Field(None, title="Knowledge Configuration")
    whatsapp_enabled: bool = Field(..., title="WhatsApp Enabled")
    whatsapp_token: str | None = Field(None, title="WhatsApp Token")
