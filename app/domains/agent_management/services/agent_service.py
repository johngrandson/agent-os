import uuid

from app.domains.agent_management.agent import Agent
from app.domains.agent_management.api.schemas import CreateAgentRequest, UpdateAgentRequest
from app.domains.agent_management.events.publisher import AgentEventPublisher
from app.domains.agent_management.repositories.agent_repository import AgentRepository
from core.exceptions.domain import AgentAlreadyExists
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
    async def create_agent(self, *, request: CreateAgentRequest) -> Agent:
        """Create a new agent"""
        existing_agent = await self.repository.get_agent_by_phone_number(
            phone_number=request.phone_number
        )
        if existing_agent:
            raise AgentAlreadyExists

        # Create agent model instance
        agent = Agent.create(
            name=request.name,
            phone_number=request.phone_number,
            description=request.description,
            instructions=request.instructions,
            is_active=request.is_active,
            default_language=request.default_language,
            llm_model=request.llm_model,
        )

        # Create agent in database
        await self.repository.create_agent(agent=agent)

        # Publish agent creation event
        await self.event_publisher.agent_created(
            agent_id=str(agent.id),
            agent_data={
                "name": agent.name,
                "is_active": agent.is_active,
                "phone_number": agent.phone_number,
                "llm_model": agent.llm_model,
                "default_language": agent.default_language,
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
    async def update_agent(self, *, agent_id: str, request: UpdateAgentRequest) -> Agent | None:
        """Update an existing agent"""
        agent_uuid = uuid.UUID(agent_id)
        agent = await self.repository.get_agent_by_id(agent_id=agent_uuid)
        if not agent:
            return None

        # Check if phone number is being changed and if new number already exists
        if request.phone_number is not None and agent.phone_number != request.phone_number:
            existing_agent = await self.repository.get_agent_by_phone_number(
                phone_number=request.phone_number
            )
            if existing_agent and str(existing_agent.id) != agent_id:
                raise AgentAlreadyExists

        # Update agent fields (only update provided fields)
        if request.name is not None:
            agent.name = request.name
        if request.phone_number is not None:
            agent.phone_number = request.phone_number
        if request.description is not None:
            agent.description = request.description
        if request.instructions is not None:
            agent.instructions = request.instructions
        if request.is_active is not None:
            agent.is_active = request.is_active
        if request.llm_model is not None:
            agent.llm_model = request.llm_model
        if request.default_language is not None:
            agent.default_language = request.default_language

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
