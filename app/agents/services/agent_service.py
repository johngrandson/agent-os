import uuid

from app.agents.agent import Agent
from app.agents.api.schemas import CreateAgentCommand, UpdateAgentCommand
from app.agents.repositories.agent_repository import AgentRepository
from app.events.agents.publisher import AgentEventPublisher
from infrastructure.database import Transactional


class AgentService:
    def __init__(
        self,
        *,
        repository: AgentRepository,
        event_publisher: AgentEventPublisher,
    ) -> None:
        self.repository = repository
        self.event_publisher = event_publisher

    async def get_agent_list(
        self,
        *,
        limit: int = 12,
        prev: int | None = None,
    ) -> list[Agent]:
        return await self.repository.get_agents(limit=limit, prev=prev)

    @Transactional()
    async def create_agent(self, *, command: CreateAgentCommand) -> Agent:
        """Create a new agent"""
        existing_agent = await self.repository.get_agent_by_phone_number(
            phone_number=command.phone_number
        )
        if existing_agent:
            from core.exceptions.domain import AgentAlreadyExists

            raise AgentAlreadyExists

        agent = Agent.create(
            name=command.name,
            phone_number=command.phone_number,
            description=command.description,
            instructions=command.instructions,
            is_active=command.is_active,
        )
        await self.repository.create_agent(agent=agent)

        # Publish agent creation event
        await self.event_publisher.agent_created(
            agent_id=str(agent.id),
            agent_data={
                "name": agent.name,
                "is_active": agent.is_active,
            },
        )

        return agent

    async def get_agent_by_id(self, *, agent_id: str) -> Agent | None:
        agent_uuid = uuid.UUID(agent_id)
        return await self.repository.get_agent_by_id(agent_id=agent_uuid)

    async def get_agent_by_id_with_relations(self, *, agent_id: str) -> Agent | None:
        agent_uuid = uuid.UUID(agent_id)
        return await self.repository.get_agent_by_id_with_relations(agent_id=agent_uuid)

    @Transactional()
    async def update_agent(self, *, command: UpdateAgentCommand) -> Agent | None:
        """Update an existing agent"""
        agent_uuid = uuid.UUID(command.agent_id)
        agent = await self.repository.get_agent_by_id(agent_id=agent_uuid)
        if not agent:
            return None

        # Check if phone number is being changed and if new number already exists
        if agent.phone_number != command.phone_number:
            existing_agent = await self.repository.get_agent_by_phone_number(
                phone_number=command.phone_number
            )
            if existing_agent and str(existing_agent.id) != command.agent_id:
                from core.exceptions.domain import AgentAlreadyExists

                raise AgentAlreadyExists

        # Update agent fields
        agent.name = command.name
        agent.phone_number = command.phone_number
        agent.description = command.description
        agent.instructions = command.instructions
        agent.is_active = command.is_active
        agent.available_tools = command.available_tools

        await self.repository.update_agent(agent=agent)

        # Publish agent update event
        await self.event_publisher.agent_updated(
            agent_id=str(agent.id),
            agent_data={
                "name": agent.name,
                "is_active": agent.is_active,
            },
        )

        return agent

    @Transactional()
    async def delete_agent(self, *, agent_id: str) -> bool:
        """Delete an agent by ID"""
        agent_uuid = uuid.UUID(agent_id)
        agent = await self.repository.get_agent_by_id(agent_id=agent_uuid)
        if not agent:
            return False

        await self.repository.delete_agent(agent=agent)

        # Publish agent deletion event
        await self.event_publisher.agent_deleted(agent_id=agent_id)

        return True
