"""
Team API schemas for request/response validation
"""

import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Team schemas
class TeamCreate(BaseModel):
    name: str = Field(..., description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    team_type: str = Field(
        "collaborative",
        description="Team type (collaborative, hierarchical, sequential, competitive)",
    )
    leader_id: Optional[str] = Field(None, description="Team leader agent ID")
    max_members: int = Field(10, description="Maximum number of team members")
    auto_assign_tasks: bool = Field(
        False, description="Automatically assign tasks to team members"
    )
    coordination_strategy: Optional[Dict[str, Any]] = Field(
        None, description="Team coordination strategy"
    )


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    team_type: Optional[str] = Field(None, description="Team type")
    leader_id: Optional[str] = Field(None, description="Team leader agent ID")
    max_members: Optional[int] = Field(
        None, description="Maximum number of team members"
    )
    auto_assign_tasks: Optional[bool] = Field(
        None, description="Automatically assign tasks"
    )
    coordination_strategy: Optional[Dict[str, Any]] = Field(
        None, description="Coordination strategy"
    )
    status: Optional[str] = Field(None, description="Team status")


class TeamMemberAdd(BaseModel):
    agent_id: str = Field(..., description="Agent ID to add to team")
    role: str = Field(
        "member", description="Member role (leader, member, coordinator, specialist)"
    )
    permissions: Optional[Dict[str, Any]] = Field(
        None, description="Member permissions"
    )


class TeamResponse(BaseModel):
    id: str = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    team_type: str = Field(..., description="Team type")
    status: str = Field(..., description="Team status")
    leader_id: Optional[str] = Field(None, description="Team leader ID")
    max_members: int = Field(..., description="Maximum team members")
    auto_assign_tasks: bool = Field(..., description="Auto-assign tasks setting")
    coordination_strategy: Optional[Dict[str, Any]] = Field(
        None, description="Coordination strategy"
    )
    total_tasks_completed: int = Field(..., description="Total completed tasks")
    success_rate: Optional[float] = Field(None, description="Team success rate")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


# Team Task schemas
class TeamTaskAssign(BaseModel):
    task_id: str = Field(..., description="Task ID to assign")
    assigned_by: Optional[str] = Field(
        None, description="Agent ID who assigned the task"
    )
    coordination_plan: Optional[Dict[str, Any]] = Field(
        None, description="Coordination plan"
    )


class TeamTaskResponse(BaseModel):
    id: str = Field(..., description="Team task ID")
    team_id: str = Field(..., description="Team ID")
    task_id: str = Field(..., description="Task ID")
    assigned_by: Optional[str] = Field(None, description="Assigned by agent ID")
    coordination_plan: Optional[Dict[str, Any]] = Field(
        None, description="Coordination plan"
    )
    status: str = Field(..., description="Task status")
    progress: float = Field(..., description="Task progress (0.0-1.0)")
    created_at: datetime = Field(..., description="Assignment timestamp")

    class Config:
        from_attributes = True


class TeamsListResponse(BaseModel):
    teams: List[TeamResponse] = Field(..., description="List of teams")
    total: int = Field(..., description="Total number of teams")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items returned")


# Team Coordination schemas
class CoordinationCreate(BaseModel):
    objective: str = Field(..., description="Coordination objective")
    strategy: str = Field(..., description="Coordination strategy")
    plan: Optional[Dict[str, Any]] = Field(None, description="Coordination plan")


class CoordinationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Coordination status")
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Progress (0.0-1.0)"
    )
    assignments: Optional[Dict[str, Any]] = Field(None, description="Task assignments")
    results: Optional[Dict[str, Any]] = Field(None, description="Coordination results")


class CoordinationResponse(BaseModel):
    id: str = Field(..., description="Coordination ID")
    team_id: str = Field(..., description="Team ID")
    objective: str = Field(..., description="Coordination objective")
    strategy: str = Field(..., description="Coordination strategy")
    status: str = Field(..., description="Coordination status")
    progress: float = Field(..., description="Progress (0.0-1.0)")
    plan: Optional[Dict[str, Any]] = Field(None, description="Coordination plan")
    assignments: Optional[Dict[str, Any]] = Field(None, description="Task assignments")
    results: Optional[Dict[str, Any]] = Field(None, description="Coordination results")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True
