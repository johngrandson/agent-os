"""
Team service for business logic and orchestration
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.teams.repositories.team_repository import TeamRepository
from app.teams.models import (
    Team,
    TeamTask,
    TeamCoordination,
)
from app.events.bus import EventBus
from app.agents.events import AgentEvent
from app.tasks.events import TaskEvent
from app.teams.events import TeamEvent


class TeamService:
    """Service for team operations and coordination"""

    def __init__(self, team_repository: TeamRepository, event_bus: EventBus):
        self.team_repository = team_repository
        self.event_bus = event_bus

    async def create_team(
        self,
        name: str,
        description: str = None,
        team_type: str = "collaborative",
        leader_id: uuid.UUID = None,
        max_members: int = 10,
        auto_assign_tasks: bool = False,
        coordination_strategy: Dict[str, Any] = None,
    ) -> Team:
        """Create a new team"""
        team = await self.team_repository.create_team(
            name=name,
            description=description,
            team_type=team_type,
            leader_id=leader_id,
            max_members=max_members,
            auto_assign_tasks=auto_assign_tasks,
            coordination_strategy=coordination_strategy,
        )

        # Emit team creation event
        await self.event_bus.emit(
            TeamEvent(
                type="team_created",
                team_id=team.id,
                data={
                    "team_name": team.name,
                    "team_type": team.team_type,
                    "leader_id": str(team.leader_id) if team.leader_id else None,
                },
            )
        )

        return team

    async def get_team(self, team_id: uuid.UUID) -> Optional[Team]:
        """Get team by ID"""
        return await self.team_repository.get_team_by_id(team_id)

    async def get_teams(self, skip: int = 0, limit: int = 100) -> List[Team]:
        """Get all teams with pagination"""
        return await self.team_repository.get_teams(skip=skip, limit=limit)

    async def get_agent_teams(self, agent_id: uuid.UUID) -> List[Team]:
        """Get teams that an agent belongs to"""
        return await self.team_repository.get_teams_by_agent(agent_id)

    async def add_team_member(
        self,
        team_id: uuid.UUID,
        agent_id: uuid.UUID,
        role: str = "member",
        permissions: Dict[str, Any] = None,
    ) -> bool:
        """Add an agent to a team"""
        # Check team capacity
        team = await self.team_repository.get_team_by_id(team_id)
        if not team:
            return False

        if len(team.members) >= team.max_members:
            return False

        success = await self.team_repository.add_team_member(
            team_id=team_id,
            agent_id=agent_id,
            role=role,
            permissions=permissions,
        )

        if success:
            # Emit member addition event
            await self.event_bus.emit(
                TeamEvent(
                    type="member_added",
                    team_id=team_id,
                    agent_id=agent_id,
                    data={
                        "team_name": team.name,
                        "role": role,
                        "permissions": permissions,
                    },
                )
            )

        return success

    async def remove_team_member(self, team_id: uuid.UUID, agent_id: uuid.UUID) -> bool:
        """Remove an agent from a team"""
        success = await self.team_repository.remove_team_member(team_id, agent_id)

        if success:
            # Emit member removal event
            await self.event_bus.emit(
                TeamEvent(
                    type="member_removed",
                    team_id=team_id,
                    agent_id=agent_id,
                    data={},
                )
            )

        return success

    async def assign_task_to_team(
        self,
        team_id: uuid.UUID,
        task_id: uuid.UUID,
        assigned_by: uuid.UUID = None,
        coordination_plan: Dict[str, Any] = None,
    ) -> TeamTask:
        """Assign a task to a team"""
        team_task = await self.team_repository.assign_task_to_team(
            team_id=team_id,
            task_id=task_id,
            assigned_by=assigned_by,
            coordination_plan=coordination_plan,
        )

        # Emit task assignment event
        await self.event_bus.emit(
            TaskEvent(
                type="task_assigned_to_team",
                task_id=task_id,
                agent_id=assigned_by,
                data={
                    "team_id": str(team_id),
                    "coordination_plan": coordination_plan,
                },
            )
        )

        # Start team coordination if auto-assignment is enabled
        team = await self.team_repository.get_team_by_id(team_id)
        if team and team.auto_assign_tasks:
            await self._auto_coordinate_task(team, team_task)

        return team_task

    async def _auto_coordinate_task(self, team: Team, team_task: TeamTask):
        """Automatically coordinate task assignment based on team type"""
        coordination_strategy = team.coordination_strategy or {}
        strategy_type = coordination_strategy.get("type", team.team_type)

        if strategy_type == "hierarchical":
            await self._coordinate_hierarchical(team, team_task)
        elif strategy_type == "sequential":
            await self._coordinate_sequential(team, team_task)
        elif strategy_type == "competitive":
            await self._coordinate_competitive(team, team_task)
        else:  # collaborative
            await self._coordinate_collaborative(team, team_task)

    async def _coordinate_hierarchical(self, team: Team, team_task: TeamTask):
        """Coordinate task in hierarchical mode - leader assigns to members"""
        if team.leader_id:
            # Create coordination session
            coordination = await self.team_repository.create_coordination_session(
                team_id=team.id,
                objective=f"Coordinate task {team_task.task_id}",
                strategy="hierarchical",
                plan={
                    "leader_id": str(team.leader_id),
                    "task_id": str(team_task.task_id),
                },
            )

            # Emit coordination event
            await self.event_bus.emit(
                TeamEvent(
                    type="coordination_started",
                    team_id=team.id,
                    data={
                        "coordination_id": str(coordination.id),
                        "strategy": "hierarchical",
                        "leader_id": str(team.leader_id),
                    },
                )
            )

    async def _coordinate_collaborative(self, team: Team, team_task: TeamTask):
        """Coordinate task in collaborative mode - all members work together"""
        coordination = await self.team_repository.create_coordination_session(
            team_id=team.id,
            objective=f"Collaborate on task {team_task.task_id}",
            strategy="collaborative",
            plan={"members": [str(member.id) for member in team.members]},
        )

        # Emit coordination event
        await self.event_bus.emit(
            TeamEvent(
                type="coordination_started",
                team_id=team.id,
                data={
                    "coordination_id": str(coordination.id),
                    "strategy": "collaborative",
                    "members_count": len(team.members),
                },
            )
        )

    async def _coordinate_sequential(self, team: Team, team_task: TeamTask):
        """Coordinate task in sequential mode - members work in order"""
        member_order = [str(member.id) for member in team.members]
        coordination = await self.team_repository.create_coordination_session(
            team_id=team.id,
            objective=f"Sequential execution of task {team_task.task_id}",
            strategy="sequential",
            plan={"sequence": member_order, "current_index": 0},
        )

        # Emit coordination event
        await self.event_bus.emit(
            TeamEvent(
                type="coordination_started",
                team_id=team.id,
                data={
                    "coordination_id": str(coordination.id),
                    "strategy": "sequential",
                    "sequence": member_order,
                },
            )
        )

    async def _coordinate_competitive(self, team: Team, team_task: TeamTask):
        """Coordinate task in competitive mode - members compete for best result"""
        coordination = await self.team_repository.create_coordination_session(
            team_id=team.id,
            objective=f"Competitive execution of task {team_task.task_id}",
            strategy="competitive",
            plan={"competitors": [str(member.id) for member in team.members]},
        )

        # Emit coordination event
        await self.event_bus.emit(
            TeamEvent(
                type="coordination_started",
                team_id=team.id,
                data={
                    "coordination_id": str(coordination.id),
                    "strategy": "competitive",
                    "competitors": len(team.members),
                },
            )
        )

    async def update_team(self, team_id: uuid.UUID, **kwargs) -> Optional[Team]:
        """Update team information"""
        team = await self.team_repository.update_team(team_id, **kwargs)

        if team:
            # Emit team update event
            await self.event_bus.emit(
                TeamEvent(
                    type="team_updated",
                    team_id=team_id,
                    data={"updated_fields": list(kwargs.keys())},
                )
            )

        return team

    async def delete_team(self, team_id: uuid.UUID) -> bool:
        """Delete a team"""
        success = await self.team_repository.delete_team(team_id)

        if success:
            # Emit team deletion event
            await self.event_bus.emit(
                TeamEvent(
                    type="team_deleted",
                    team_id=team_id,
                    data={},
                )
            )

        return success
