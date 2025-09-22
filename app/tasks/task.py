"""
Task entity models for the task management system
"""

from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import String, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database import Base
from infrastructure.database.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.agents.agent import Agent


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    """Types of tasks that can be executed"""

    SIMPLE = "simple"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    SUPPORT = "support"


class Task(Base, TimestampMixin):
    """Task entity for managing agent tasks"""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority), nullable=False, default=TaskPriority.NORMAL
    )

    # Assignment
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("agents.id"), nullable=True
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Task hierarchy
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )

    # Task configuration and results
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    expected_tools: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution tracking
    started_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    execution_time: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    assigned_agent: Mapped[Optional["Agent"]] = relationship(
        "Agent", back_populates="assigned_tasks"
    )
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side=[id], back_populates="subtasks"
    )
    subtasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="parent_task", cascade="all, delete-orphan"
    )

    @classmethod
    def create(
        cls,
        *,
        title: str,
        description: str = None,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.NORMAL,
        assigned_agent_id: uuid.UUID = None,
        assigned_by: str = None,
        parent_task_id: uuid.UUID = None,
        parameters: Dict[str, Any] = None,
        expected_tools: List[str] = None,
    ) -> "Task":
        return cls(
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            assigned_agent_id=assigned_agent_id,
            assigned_by=assigned_by,
            parent_task_id=parent_task_id,
            parameters=parameters,
            expected_tools=expected_tools,
        )

    def start_execution(self):
        """Mark task as started"""
        from datetime import datetime

        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow().isoformat()

    def complete_execution(self, results: Dict[str, Any] = None):
        """Mark task as completed"""
        from datetime import datetime

        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()
        if results:
            self.results = results

        # Calculate execution time
        if self.started_at and self.completed_at:
            from datetime import datetime

            start_time = datetime.fromisoformat(self.started_at)
            end_time = datetime.fromisoformat(self.completed_at)
            self.execution_time = (end_time - start_time).total_seconds()

    def fail_execution(self, error_message: str):
        """Mark task as failed"""
        from datetime import datetime

        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow().isoformat()
        self.error_message = error_message

    def cancel_execution(self):
        """Mark task as cancelled"""
        from datetime import datetime

        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow().isoformat()


class TaskRead(BaseModel):
    """Task read model for API responses"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., title="Task ID")
    title: str = Field(..., title="Title")
    description: Optional[str] = Field(None, title="Description")
    task_type: TaskType = Field(..., title="Task Type")
    status: TaskStatus = Field(..., title="Status")
    priority: TaskPriority = Field(..., title="Priority")
    assigned_agent_id: Optional[str] = Field(None, title="Assigned Agent ID")
    assigned_by: Optional[str] = Field(None, title="Assigned By")
    parent_task_id: Optional[str] = Field(None, title="Parent Task ID")
    parameters: Optional[Dict[str, Any]] = Field(None, title="Parameters")
    expected_tools: Optional[List[str]] = Field(None, title="Expected Tools")
    results: Optional[Dict[str, Any]] = Field(None, title="Results")
    error_message: Optional[str] = Field(None, title="Error Message")
    started_at: Optional[str] = Field(None, title="Started At")
    completed_at: Optional[str] = Field(None, title="Completed At")
    execution_time: Optional[float] = Field(None, title="Execution Time")
