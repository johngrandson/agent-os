"""Agent Repository - direct SQLAlchemy implementation"""

import uuid

from app.agents.agent import Agent
from infrastructure.database.session import get_session
from sqlalchemy import select


class AgentRepository:
    """Simplified agent repository with direct SQLAlchemy implementation"""

    async def get_agents(
        self,
        *,
        limit: int = 12,
        prev: int | None = None,
    ) -> list[Agent]:
        """Get paginated list of agents with relationships"""
        async with get_session() as session:
            query = select(Agent)

            if prev:
                query = query.where(Agent.id < prev)

            if limit > 12:
                limit = 12

            query = query.limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_agent_by_id(self, *, agent_id: uuid.UUID) -> Agent | None:
        """Find agent by ID"""
        async with get_session() as session:
            result = await session.execute(select(Agent).where(Agent.id == agent_id))
            return result.scalars().first()

    async def get_agent_by_id_with_relations(self, *, agent_id: uuid.UUID) -> Agent | None:
        """Find agent by ID with config eagerly loaded"""
        async with get_session() as session:
            stmt = select(Agent).where(Agent.id == agent_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_agent_by_phone_number(self, *, phone_number: str) -> Agent | None:
        """Find agent by phone number"""
        async with get_session() as session:
            result = await session.execute(select(Agent).where(Agent.phone_number == phone_number))
            return result.scalars().first()

    async def get_agents_by_status(
        self,
        *,
        status: bool,
        limit: int = 12,
    ) -> list[Agent]:
        """Get agents by status"""
        async with get_session() as session:
            query = select(Agent).where(Agent.is_active == status).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def create_agent(self, *, agent: Agent) -> Agent:
        """Create a new agent"""
        async with get_session() as session:
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
            return agent

    async def update_agent(self, *, agent: Agent) -> Agent:
        """Update existing agent"""
        async with get_session() as session:
            merged_agent = await session.merge(agent)
            await session.commit()
            await session.refresh(merged_agent)
            return merged_agent

    async def delete_agent(self, *, agent: Agent) -> None:
        """Delete agent"""
        async with get_session() as session:
            # Get the agent from current session to ensure it's tracked
            tracked_agent = await session.get(Agent, agent.id)
            if tracked_agent:
                await session.delete(tracked_agent)
                await session.commit()
