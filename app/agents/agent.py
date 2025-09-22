from __future__ import annotations

import uuid
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import String, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database import Base
from infrastructure.database.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.knowledge.knowledge import KnowledgeContent
    from app.tasks.task import Task


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

    # New fields for specialization and tools
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    available_tools: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    tool_configurations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    knowledge_contents: Mapped[List["KnowledgeContent"]] = relationship(
        "KnowledgeContent",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="assigned_agent",
        cascade="all, delete-orphan",
    )

    # Teams relationship
    teams: Mapped[List["Team"]] = relationship(
        "Team", secondary="team_members", back_populates="members", lazy="selectin"
    )

    @classmethod
    def create(
        cls,
        *,
        name: str,
        phone_number: str,
        description: str = None,
        instructions: List[str] = None,
        is_active: bool,
        role: str = None,
        specialization: str = None,
        available_tools: List[str] = None,
        tool_configurations: dict = None,
    ) -> "Agent":
        return cls(
            name=name,
            phone_number=phone_number,
            description=description,
            instructions=instructions,
            is_active=is_active,
            role=role,
            specialization=specialization,
            available_tools=available_tools,
            tool_configurations=tool_configurations,
        )


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., title="Agent ID")
    name: str = Field(..., title="Name")
    phone_number: str = Field(..., title="Phone Number")
    description: Optional[str] = Field(None, title="Description")
    is_active: bool = Field(..., title="Is Active")
    role: Optional[str] = Field(None, title="Agent Role")
    specialization: Optional[str] = Field(None, title="Specialization")
    available_tools: Optional[List[str]] = Field(None, title="Available Tools")
    tool_configurations: Optional[dict] = Field(None, title="Tool Configurations")
