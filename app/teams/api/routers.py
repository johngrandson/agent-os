"""
Team API routers for FastAPI endpoints
"""

import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query
from dependency_injector.wiring import inject, Provide

from app.container import ApplicationContainer as Container
from app.teams.services.team_service import TeamService
from app.teams.api.schemas import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamMemberAdd,
    TeamsListResponse,
    TeamTaskAssign,
    TeamTaskResponse,
    CoordinationCreate,
    CoordinationUpdate,
    CoordinationResponse,
)

router = APIRouter(tags=["teams"])


# Team endpoints
@router.post("/teams", response_model=TeamResponse, status_code=201)
@inject
async def create_team(
    team_data: TeamCreate,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Create a new team"""
    try:
        leader_id = uuid.UUID(team_data.leader_id) if team_data.leader_id else None
        team = await team_service.create_team(
            name=team_data.name,
            description=team_data.description,
            team_type=team_data.team_type,
            leader_id=leader_id,
            max_members=team_data.max_members,
            auto_assign_tasks=team_data.auto_assign_tasks,
            coordination_strategy=team_data.coordination_strategy,
        )
        return TeamResponse.model_validate(team)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")


@router.get("/teams", response_model=TeamsListResponse)
@inject
async def get_teams(
    skip: int = Query(0, ge=0, description="Number of teams to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of teams to return"
    ),
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Get all teams with pagination"""
    try:
        teams = await team_service.get_teams(skip=skip, limit=limit)
        team_responses = [TeamResponse.model_validate(team) for team in teams]
        return TeamsListResponse(
            teams=team_responses,
            total=len(team_responses),
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get teams: {str(e)}")


@router.get("/teams/{team_id}", response_model=TeamResponse)
@inject
async def get_team(
    team_id: str,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Get a specific team by ID"""
    try:
        team_uuid = uuid.UUID(team_id)
        team = await team_service.get_team(team_uuid)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return TeamResponse.model_validate(team)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")


@router.put("/teams/{team_id}", response_model=TeamResponse)
@inject
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Update a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        update_data = team_data.model_dump(exclude_unset=True)

        # Convert leader_id to UUID if provided
        if "leader_id" in update_data and update_data["leader_id"]:
            update_data["leader_id"] = uuid.UUID(update_data["leader_id"])

        team = await team_service.update_team(team_uuid, **update_data)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return TeamResponse.model_validate(team)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update team: {str(e)}")


@router.delete("/teams/{team_id}", status_code=204)
@inject
async def delete_team(
    team_id: str,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Delete a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        success = await team_service.delete_team(team_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete team: {str(e)}")


# Team member endpoints
@router.post("/teams/{team_id}/members", status_code=201)
@inject
async def add_team_member(
    team_id: str,
    member_data: TeamMemberAdd,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Add a member to a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        agent_uuid = uuid.UUID(member_data.agent_id)

        success = await team_service.add_team_member(
            team_id=team_uuid,
            agent_id=agent_uuid,
            role=member_data.role,
            permissions=member_data.permissions,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to add member (team not found, member already exists, or capacity exceeded)",
            )

        return {"message": "Member added successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add team member: {str(e)}"
        )


@router.delete("/teams/{team_id}/members/{agent_id}", status_code=204)
@inject
async def remove_team_member(
    team_id: str,
    agent_id: str,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Remove a member from a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        agent_uuid = uuid.UUID(agent_id)

        success = await team_service.remove_team_member(team_uuid, agent_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Team member not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to remove team member: {str(e)}"
        )


@router.get("/agents/{agent_id}/teams", response_model=TeamsListResponse)
@inject
async def get_agent_teams(
    agent_id: str,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Get all teams that an agent belongs to"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        teams = await team_service.get_agent_teams(agent_uuid)
        team_responses = [TeamResponse.model_validate(team) for team in teams]
        return TeamsListResponse(
            teams=team_responses,
            total=len(team_responses),
            skip=0,
            limit=len(team_responses),
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent teams: {str(e)}"
        )


# Team task endpoints
@router.post("/teams/{team_id}/tasks", response_model=TeamTaskResponse, status_code=201)
@inject
async def assign_task_to_team(
    team_id: str,
    task_data: TeamTaskAssign,
    team_service: TeamService = Depends(Provide[Container.team_service]),
):
    """Assign a task to a team"""
    try:
        team_uuid = uuid.UUID(team_id)
        task_uuid = uuid.UUID(task_data.task_id)
        assigned_by_uuid = (
            uuid.UUID(task_data.assigned_by) if task_data.assigned_by else None
        )

        team_task = await team_service.assign_task_to_team(
            team_id=team_uuid,
            task_id=task_uuid,
            assigned_by=assigned_by_uuid,
            coordination_plan=task_data.coordination_plan,
        )

        return TeamTaskResponse.model_validate(team_task)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to assign task to team: {str(e)}"
        )
