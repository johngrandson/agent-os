"""
Team models for agent coordination
"""

import uuid
from enum import Enum
from typing import Dict, Any, List
from sqlalchemy import String, Text, Boolean, Integer, JSON, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base
from infrastructure.database.mixins.timestamp_mixin import TimestampMixin


class TeamType(str, Enum):
    """Types of teams"""

    COLLABORATIVE = "collaborative"  # All agents work together
    HIERARCHICAL = "hierarchical"  # Leader delegates to members
    SEQUENTIAL = "sequential"  # Agents work in sequence
    COMPETITIVE = "competitive"  # Agents compete for best result


class TeamStatus(str, Enum):
    """Team status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class MemberRole(str, Enum):
    """Roles of team members"""

    LEADER = "leader"
    MEMBER = "member"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


# Association table for team-agent many-to-many relationship
team_members = Table(
    "team_members",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False),
    Column("agent_id", UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False),
    Column("role", String(50), nullable=False, default=MemberRole.MEMBER.value),
    Column("permissions", JSON, nullable=True),
    Column("joined_at", String, nullable=False),
    Column("is_active", Boolean, default=True),
)


class Team(Base, TimestampMixin):
    """Team model for agent coordination"""

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Team configuration
    team_type: Mapped[TeamType] = mapped_column(
        String(50), nullable=False, default=TeamType.COLLABORATIVE.value
    )
    status: Mapped[TeamStatus] = mapped_column(
        String(50), nullable=False, default=TeamStatus.ACTIVE.value
    )

    # Team leader (optional)
    leader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )

    # Team settings
    max_members: Mapped[int] = mapped_column(Integer, default=10)
    auto_assign_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    coordination_strategy: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Metrics
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(nullable=True)

    # Relationships
    members: Mapped[List["Agent"]] = relationship(
        "Agent", secondary=team_members, back_populates="teams", lazy="selectin"
    )

    leader: Mapped["Agent"] = relationship(
        "Agent", foreign_keys=[leader_id], lazy="selectin"
    )


class TeamTask(Base, TimestampMixin):
    """Tasks assigned to teams"""

    __tablename__ = "team_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )

    # Assignment details
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    coordination_plan: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    progress: Mapped[float] = mapped_column(default=0.0)

    # Relationships
    team: Mapped["Team"] = relationship("Team", lazy="selectin")
    task: Mapped["Task"] = relationship("Task", lazy="selectin")
    assigned_by_agent: Mapped["Agent"] = relationship(
        "Agent", foreign_keys=[assigned_by], lazy="selectin"
    )


class TeamCoordination(Base, TimestampMixin):
    """Team coordination sessions"""

    __tablename__ = "team_coordinations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False
    )

    # Coordination details
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="planning")
    progress: Mapped[float] = mapped_column(default=0.0)

    # Coordination data
    plan: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    assignments: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    results: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Timeline
    started_at: Mapped[str] = mapped_column(nullable=True)
    completed_at: Mapped[str] = mapped_column(nullable=True)

    # Relationships
    team: Mapped["Team"] = relationship("Team", lazy="selectin")
