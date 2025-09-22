"""
Team repository for database operations
"""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload

from infrastructure.database.session import get_session
from app.teams.models import (
    Team,
    TeamTask,
    TeamCoordination,
    team_members,
)
from app.agents.agent import Agent


class TeamRepository:
    """Repository for team-related database operations"""

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
        async with get_session() as session:
            team = Team(
                name=name,
                description=description,
                team_type=team_type,
                leader_id=leader_id,
                max_members=max_members,
                auto_assign_tasks=auto_assign_tasks,
                coordination_strategy=coordination_strategy,
            )
            session.add(team)
            await session.commit()
            await session.refresh(team)
            return team

    async def get_team_by_id(self, team_id: uuid.UUID) -> Optional[Team]:
        """Get team by ID with members"""
        async with get_session() as session:
            query = (
                select(Team)
                .options(selectinload(Team.members), selectinload(Team.leader))
                .where(Team.id == team_id)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_teams(self, skip: int = 0, limit: int = 100) -> List[Team]:
        """Get all teams with pagination"""
        async with get_session() as session:
            query = (
                select(Team)
                .options(selectinload(Team.members), selectinload(Team.leader))
                .offset(skip)
                .limit(limit)
                .order_by(Team.created_at.desc())
            )
            result = await session.execute(query)
            return result.scalars().all()

    async def get_teams_by_agent(self, agent_id: uuid.UUID) -> List[Team]:
        """Get teams that an agent belongs to"""
        async with get_session() as session:
            query = (
                select(Team)
                .options(selectinload(Team.members), selectinload(Team.leader))
                .join(team_members)
                .where(team_members.c.agent_id == agent_id)
                .where(team_members.c.is_active == True)
            )
            result = await session.execute(query)
            return result.scalars().all()

    async def add_team_member(
        self,
        team_id: uuid.UUID,
        agent_id: uuid.UUID,
        role: str = "member",
        permissions: Dict[str, Any] = None,
    ) -> bool:
        """Add an agent to a team"""
        async with get_session() as session:
            # Check if member already exists
            existing_query = select(team_members).where(
                and_(
                    team_members.c.team_id == team_id,
                    team_members.c.agent_id == agent_id,
                )
            )
            existing = await session.execute(existing_query)
            if existing.first():
                return False

            # Add new member
            insert_stmt = team_members.insert().values(
                team_id=team_id,
                agent_id=agent_id,
                role=role,
                permissions=permissions,
                joined_at=func.now(),
                is_active=True,
            )
            await session.execute(insert_stmt)
            await session.commit()
            return True

    async def remove_team_member(self, team_id: uuid.UUID, agent_id: uuid.UUID) -> bool:
        """Remove an agent from a team"""
        async with get_session() as session:
            update_stmt = (
                update(team_members)
                .where(
                    and_(
                        team_members.c.team_id == team_id,
                        team_members.c.agent_id == agent_id,
                    )
                )
                .values(is_active=False)
            )
            result = await session.execute(update_stmt)
            await session.commit()
            return result.rowcount > 0

    async def update_team(self, team_id: uuid.UUID, **kwargs) -> Optional[Team]:
        """Update team information"""
        async with get_session() as session:
            query = update(Team).where(Team.id == team_id).values(**kwargs)
            await session.execute(query)
            await session.commit()
            return await self.get_team_by_id(team_id)

    async def delete_team(self, team_id: uuid.UUID) -> bool:
        """Delete a team"""
        async with get_session() as session:
            query = delete(Team).where(Team.id == team_id)
            result = await session.execute(query)
            await session.commit()
            return result.rowcount > 0

    # Team Task methods
    async def assign_task_to_team(
        self,
        team_id: uuid.UUID,
        task_id: uuid.UUID,
        assigned_by: uuid.UUID = None,
        coordination_plan: Dict[str, Any] = None,
    ) -> TeamTask:
        """Assign a task to a team"""
        async with get_session() as session:
            team_task = TeamTask(
                team_id=team_id,
                task_id=task_id,
                assigned_by=assigned_by,
                coordination_plan=coordination_plan,
            )
            session.add(team_task)
            await session.commit()
            await session.refresh(team_task)
            return team_task

    async def get_team_tasks(self, team_id: uuid.UUID) -> List[TeamTask]:
        """Get all tasks assigned to a team"""
        async with get_session() as session:
            query = (
                select(TeamTask)
                .options(
                    selectinload(TeamTask.team),
                    selectinload(TeamTask.task),
                    selectinload(TeamTask.assigned_by_agent),
                )
                .where(TeamTask.team_id == team_id)
            )
            result = await session.execute(query)
            return result.scalars().all()

    # Team Coordination methods
    async def create_coordination_session(
        self,
        team_id: uuid.UUID,
        objective: str,
        strategy: str,
        plan: Dict[str, Any] = None,
    ) -> TeamCoordination:
        """Create a new coordination session"""
        async with get_session() as session:
            coordination = TeamCoordination(
                team_id=team_id,
                objective=objective,
                strategy=strategy,
                plan=plan,
            )
            session.add(coordination)
            await session.commit()
            await session.refresh(coordination)
            return coordination

    async def update_coordination_progress(
        self,
        coordination_id: uuid.UUID,
        progress: float,
        status: str = None,
        assignments: Dict[str, Any] = None,
        results: Dict[str, Any] = None,
    ) -> Optional[TeamCoordination]:
        """Update coordination session progress"""
        async with get_session() as session:
            update_data = {"progress": progress}
            if status:
                update_data["status"] = status
            if assignments:
                update_data["assignments"] = assignments
            if results:
                update_data["results"] = results

            query = (
                update(TeamCoordination)
                .where(TeamCoordination.id == coordination_id)
                .values(**update_data)
            )
            await session.execute(query)
            await session.commit()

            # Return updated coordination
            get_query = select(TeamCoordination).where(
                TeamCoordination.id == coordination_id
            )
            result = await session.execute(get_query)
            return result.scalar_one_or_none()
