from __future__ import annotations

import uuid
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import String, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database import Base
from infrastructure.database.mixins import TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    instructions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)

    # Tool configuration fields
    available_tools: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    tool_configurations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Knowledge configuration field
    knowledge_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        phone_number: str,
        description: str = None,
        instructions: List[str] = None,
        is_active: bool,
        available_tools: List[str] = None,
        tool_configurations: dict = None,
        knowledge_config: dict = None,
    ) -> "Agent":
        return cls(
            name=name,
            phone_number=phone_number,
            description=description,
            instructions=instructions,
            is_active=is_active,
            available_tools=available_tools,
            tool_configurations=tool_configurations,
            knowledge_config=knowledge_config,
        )


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., title="Agent ID")
    name: str = Field(..., title="Name")
    phone_number: str = Field(..., title="Phone Number")
    description: Optional[str] = Field(None, title="Description")
    is_active: bool = Field(..., title="Is Active")
    available_tools: Optional[List[str]] = Field(None, title="Available Tools")
    tool_configurations: Optional[dict] = Field(None, title="Tool Configurations")
