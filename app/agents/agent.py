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
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="pt-BR")


    @classmethod
    def create(
        cls,
        *,
        name: str,
        phone_number: str,
        description: str | None = None,
        instructions: list[str] | None = None,
        is_active: bool,
        llm_model: str | None = None,
        default_language: str | None = "pt-BR",
    ) -> Agent:
        return cls(
            name=name,
            phone_number=phone_number,
            description=description,
            instructions=instructions,
            is_active=is_active,
            llm_model=llm_model,
            default_language=default_language,
        )


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., title="Agent ID")
    name: str = Field(..., title="Name")
    phone_number: str = Field(..., title="Phone Number")
    description: str | None = Field(None, title="Description")
    instructions: list[str] | None = Field(None, title="Instructions")
    is_active: bool = Field(..., title="Is Active")
    llm_model: str | None = Field(None, title="LLM Model")
    default_language: str | None = Field("pt-BR", title="Default Language")
