import uuid

from app.agents.repositories.agent_repository import AgentRepository
from app.agents.api.schemas import CreateAgentCommand, UpdateAgentCommand
from app.agents.agent import Agent
from app.tools.registry import ToolRegistry
from app.events.bus import EventBus
from app.agents.events import AgentEvent
from app.tools.events import ToolEvent
from infrastructure.database import Transactional


class AgentService:
    def __init__(
        self,
        *,
        repository: AgentRepository,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.tool_registry = tool_registry

    async def get_agent_list(
        self,
        *,
        limit: int = 12,
        prev: int | None = None,
    ) -> list[Agent]:
        return await self.repository.get_agents(limit=limit, prev=prev)

    @Transactional()
    async def create_agent(self, *, command: CreateAgentCommand) -> Agent:
        existing_agent = await self.repository.get_agent_by_phone_number(
            phone_number=command.phone_number
        )
        if existing_agent:
            from core.exceptions.domain import AgentAlreadyExists

            raise AgentAlreadyExists()

        # Validate tools exist in registry
        available_tools = command.available_tools or []
        available_tools = [
            tool for tool in available_tools if self.tool_registry.get_tool(tool)
        ]

        agent = Agent.create(
            name=command.name,
            phone_number=command.phone_number,
            description=command.description,
            instructions=command.instructions,
            is_active=command.is_active,
            available_tools=available_tools,
            tool_configurations=command.tool_configurations,
        )
        await self.repository.create_agent(agent=agent)

        # Emit agent creation event
        await self.event_bus.emit(
            AgentEvent.agent_created(
                agent_id=str(agent.id),
                data={
                    "name": agent.name,
                    "available_tools": agent.available_tools,
                    "is_active": agent.is_active,
                },
            )
        )

        return agent

    async def get_agent_by_id(self, *, agent_id: uuid.UUID) -> Agent | None:
        return await self.repository.get_agent_by_id(agent_id=agent_id)

    async def get_agent_by_id_with_relations(
        self, *, agent_id: uuid.UUID
    ) -> Agent | None:
        return await self.repository.get_agent_by_id_with_relations(agent_id=agent_id)

    @Transactional()
    async def update_agent(self, *, command: UpdateAgentCommand) -> Agent | None:
        """Update an existing agent"""
        agent = await self.repository.get_agent_by_id(agent_id=command.agent_id)
        if not agent:
            return None

        # Check if phone number is being changed and if new number already exists
        if agent.phone_number != command.phone_number:
            existing_agent = await self.repository.get_agent_by_phone_number(
                phone_number=command.phone_number
            )
            if existing_agent and existing_agent.id != command.agent_id:
                from core.exceptions.domain import AgentAlreadyExists

                raise AgentAlreadyExists()

        # Update agent fields
        agent.name = command.name
        agent.phone_number = command.phone_number
        agent.description = command.description
        agent.instructions = command.instructions
        agent.is_active = command.is_active
        agent.available_tools = command.available_tools
        agent.tool_configurations = command.tool_configurations

        # Validate tools exist in registry
        if agent.available_tools:
            agent.available_tools = [
                tool
                for tool in agent.available_tools
                if self.tool_registry.get_tool(tool)
            ]

        await self.repository.update(agent=agent)

        # Emit agent update event
        await self.event_bus.emit(
            AgentEvent.agent_updated(
                agent_id=str(agent.id),
                data={
                    "name": agent.name,
                    "available_tools": agent.available_tools,
                    "is_active": agent.is_active,
                },
            )
        )

        return agent

    @Transactional()
    async def delete_agent(self, *, agent_id: uuid.UUID) -> bool:
        """Delete an agent by ID"""
        agent = await self.repository.get_agent_by_id(agent_id=agent_id)
        if not agent:
            return False

        # Store agent data before deletion for event
        agent_data = {
            "name": agent.name,
        }

        await self.repository.delete(agent=agent)

        # Emit agent deletion event
        await self.event_bus.emit(
            AgentEvent.agent_deleted(
                agent_id=str(agent_id),
                data=agent_data,
            )
        )

        return True

    async def get_agent_capabilities(self, *, agent_id: uuid.UUID) -> dict:
        """Get agent capabilities including available tools"""
        agent = await self.repository.get_agent_by_id(agent_id=agent_id)
        if not agent:
            return None

        # Get tool definitions for agent's tools
        tool_definitions = []
        if agent.available_tools:
            for tool_name in agent.available_tools:
                tool = self.tool_registry.get_tool(tool_name)
                if tool:
                    tool_definitions.append(
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "category": tool.category,
                            "definition": tool.get_definition().dict(),
                        }
                    )

        return {
            "agent_id": str(agent.id),
            "name": agent.name,
            "available_tools": agent.available_tools or [],
            "tool_definitions": tool_definitions,
            "tool_configurations": agent.tool_configurations or {},
        }

    async def execute_agent_tool(
        self,
        *,
        agent_id: uuid.UUID,
        tool_name: str,
        parameters: dict,
        timeout: float = None,
    ) -> dict:
        """Execute a tool on behalf of an agent"""
        agent = await self.repository.get_agent_by_id(agent_id=agent_id)
        if not agent:
            return {"error": "Agent not found"}

        # Check if agent has access to this tool
        if not agent.available_tools or tool_name not in agent.available_tools:
            return {"error": f"Agent does not have access to tool '{tool_name}'"}

        # Execute the tool
        result = await self.tool_registry.execute_tool(
            tool_name=tool_name, parameters=parameters, timeout=timeout
        )

        # Emit tool execution event
        if result.error:
            await self.event_bus.emit(
                ToolEvent.tool_failed(
                    tool_name=tool_name, agent_id=str(agent.id), error=result.error
                )
            )
        else:
            await self.event_bus.emit(
                ToolEvent.tool_executed(
                    tool_name=tool_name,
                    agent_id=str(agent.id),
                    results={
                        "execution_time": result.execution_time,
                        "status": result.status.value,
                    },
                )
            )

        return {
            "agent_id": str(agent.id),
            "tool_name": tool_name,
            "status": result.status.value,
            "data": result.data,
            "error": result.error,
            "execution_time": result.execution_time,
        }
