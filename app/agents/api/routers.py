"""Agent API routers - consolidated FastAPI endpoints"""

from app.agents.api.schemas import (
    AgentResponse,
    CreateAgentCommand,
    CreateAgentRequest,
    CreateAgentResponse,
    UpdateAgentCommand,
    UpdateAgentRequest,
)
from app.agents.services.agent_service import AgentService
from app.container import Container
from core.exceptions.domain import AgentNotFound
from dependency_injector.wiring import Provide, inject

from fastapi import APIRouter, Depends, HTTPException, Query


agent_router = APIRouter()


@agent_router.get(
    "",
    response_model=list[AgentResponse],
    summary="Get list of agents",
    description="""
    Retrieve a paginated list of all agents in the system.

    **Parameters:**
    - **limit**: Maximum number of agents to return (default: 10, max: 12)
    - **prev**: ID of the previous agent for pagination (optional)

    **Returns:**
    A list of agent objects with their basic information.
    """,
)
@inject
async def get_agent_list(
    limit: int = Query(10, description="Maximum number of agents to return", ge=1, le=12),
    prev: int = Query(None, description="ID of the previous agent for pagination"),
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
):
    """Get paginated list of agents with optional filtering"""
    agents = await agent_service.get_agent_list(limit=limit, prev=prev)
    return [AgentResponse.model_validate(agent) for agent in agents]


@agent_router.post(
    "",
    response_model=CreateAgentResponse,
    status_code=201,
    summary="Create a new agent",
    description="""
    Create a new agent in the system.

    **Required fields:**
    - **name**: Agent's display name
    - **phone_number**: Unique phone number for the agent
    - **is_active**: Whether the agent is active (true) or inactive (false, default)

    **Returns:**
    The created agent's basic information.
    """,
)
@inject
async def create_agent(
    request: CreateAgentRequest,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
):
    """Create a new agent with the provided information"""
    command = CreateAgentCommand(**request.model_dump())
    agent = await agent_service.create_agent(command=command)
    return CreateAgentResponse(id=agent.id, name=agent.name, phone_number=agent.phone_number)


@agent_router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID",
    description=(
        "Retrieve a specific agent by ID with all relationships (prompts and configuration)"
    ),
)
@inject
async def get_agent(
    agent_id: str,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
):
    """Get agent by ID with relationships"""
    agent = await agent_service.get_agent_by_id_with_relations(agent_id=agent_id)
    if not agent:
        raise AgentNotFound
    return AgentResponse.model_validate(agent)


@agent_router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update an agent",
    description="""
    Update an existing agent's information.

    **Path parameter:**
    - **agent_id**: The ID of the agent to update

    **Request body:**
    - **name**: Updated agent name (optional)
    - **phone_number**: Updated phone number (optional)
    - **is_active**: Updated active status (optional)

    **Returns:**
    The updated agent's information.
    """,
)
@inject
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
):
    """Update an existing agent"""
    try:
        # Get current agent to fill in missing fields
        current_agent = await agent_service.get_agent_by_id(agent_id=agent_id)
        if not current_agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Create command with current values as defaults for optional fields
        command = UpdateAgentCommand(
            agent_id=agent_id,
            name=request.name if request.name is not None else current_agent.name,
            phone_number=request.phone_number
            if request.phone_number is not None
            else current_agent.phone_number,
            description=request.description
            if request.description is not None
            else current_agent.description,
            instructions=request.instructions
            if request.instructions is not None
            else current_agent.instructions,
            is_active=request.is_active
            if request.is_active is not None
            else current_agent.is_active,
            role=request.role if request.role is not None else current_agent.role,
            specialization=request.specialization
            if request.specialization is not None
            else current_agent.specialization,
            available_tools=request.available_tools
            if request.available_tools is not None
            else current_agent.available_tools,
            tool_configurations=request.tool_configurations
            if request.tool_configurations is not None
            else current_agent.tool_configurations,
        )

        updated_agent = await agent_service.update_agent(command=command)
        if not updated_agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return AgentResponse.model_validate(updated_agent)

    except HTTPException:
        raise
    except Exception as e:
        if "AgentAlreadyExists" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Agent with this phone number already exists",
            ) from e
        raise


@agent_router.delete(
    "/{agent_id}",
    status_code=204,
    summary="Delete an agent",
    description="""
    Delete an agent and all related data (cascade delete).

    **Path parameter:**
    - **agent_id**: The ID of the agent to delete

    **Note:** This operation will also delete all related:
    - Agent configurations
    - Prompts
    - Customers
    """,
)
@inject
async def delete_agent(
    agent_id: str,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
):
    """Delete an agent by ID"""
    success = await agent_service.delete_agent(agent_id=agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}
