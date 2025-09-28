"""Agent API routers - consolidated FastAPI endpoints"""

from app.container import Container
from app.domains.agent_management.api.schemas import (
    AgentResponse,
    CreateAgentRequest,
    CreateAgentResponse,
    UpdateAgentRequest,
)
from app.domains.agent_management.services.agent_service import AgentService
from core.exceptions.domain import AgentNotFound
from dependency_injector.wiring import Provide, inject
from fastapi.responses import Response

from fastapi import APIRouter, Depends, HTTPException, Query


agent_router = APIRouter()
agent_router.tags = ["API Agents"]


@agent_router.get(
    "",
    response_model=list[AgentResponse],
    summary="Get list of agents",
    description="""
    Retrieve a paginated list of all agents in the system.

    Parameters:
    - limit: Maximum number of agents to return (default: 10, max: 12)
    - prev: ID of the previous agent for pagination (optional)

    Returns:
    A list of agent objects with their basic information.
    """,
)
@inject
async def get_agent_list(
    limit: int = Query(10, description="Maximum number of agents to return", ge=1, le=12),
    prev: int | None = Query(None, description="ID of the previous agent for pagination"),
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
) -> list[AgentResponse]:
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

    Required fields:
    - name: Agent's display name
    - phone_number: Unique phone number for the agent
    - is_active: Whether the agent is active (true) or inactive (false, default)

    Returns:
    The created agent's basic information.
    """,
)
@inject
async def create_agent(
    request: CreateAgentRequest,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
) -> CreateAgentResponse:
    """Create a new agent with the provided information"""
    agent = await agent_service.create_agent(request=request)
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
) -> AgentResponse:
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

    Path parameter:
    - agent_id: The ID of the agent to update

    Request body:
    - name: Updated agent name (optional)
    - phone_number: Updated phone number (optional)
    - is_active: Updated active status (optional)

    Returns:
    The updated agent's information.
    """,
)
@inject
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
) -> AgentResponse:
    """Update an existing agent"""
    try:
        updated_agent = await agent_service.update_agent(agent_id=agent_id, request=request)
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

    Path parameter:
    - agent_id: The ID of the agent to delete

    Note: This operation will also delete all related:
    - Agent configurations
    - Prompts
    - Customers
    """,
)
@inject
async def delete_agent(
    agent_id: str,
    agent_service: AgentService = Depends(Provide[Container.agent_service]),
) -> Response:
    """Delete an agent by ID"""
    success = await agent_service.delete_agent(agent_id=agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Response(status_code=204)
