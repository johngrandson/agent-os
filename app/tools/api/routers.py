"""
API routes for tool management
"""

from typing import Optional, List
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, HTTPException, Query, Depends
from app.container import ApplicationContainer as Container
from app.tools.api.schemas import (
    ToolExecutionRequest,
    ToolExecutionResponse,
    ToolDefinitionResponse,
    ToolListResponse,
)
from app.tools.registry import ToolRegistry
from app.tools.loader import get_available_tools

router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=ToolListResponse)
@inject
async def list_tools(
    category: Optional[str] = Query(None, description="Filter by category"),
    tool_registry: ToolRegistry = Depends(Provide[Container.tool_registry]),
):
    """List all available tools"""
    available_tools = get_available_tools(tool_registry)

    if category:
        available_tools = [
            tool for tool in available_tools if tool["category"] == category
        ]

    tool_responses = [
        ToolDefinitionResponse(
            name=tool["name"],
            description=tool["description"],
            category=tool["category"],
            definition=tool["definition"],
        )
        for tool in available_tools
    ]

    return ToolListResponse(tools=tool_responses, total_count=len(tool_responses))


@router.get("/tools/{tool_name}", response_model=ToolDefinitionResponse)
@inject
async def get_tool(
    tool_name: str,
    tool_registry: ToolRegistry = Depends(Provide[Container.tool_registry]),
):
    """Get detailed information about a specific tool"""
    tool = tool_registry.get_tool(tool_name)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return ToolDefinitionResponse(
        name=tool.name,
        description=tool.description,
        category=tool.category,
        definition=tool.get_definition().dict(),
    )


@router.post("/tools/execute", response_model=ToolExecutionResponse)
@inject
async def execute_tool(
    request: ToolExecutionRequest,
    tool_registry: ToolRegistry = Depends(Provide[Container.tool_registry]),
):
    """Execute a tool with given parameters"""

    result = await tool_registry.execute_tool(
        tool_name=request.tool_name,
        parameters=request.parameters,
        timeout=request.timeout,
    )

    return ToolExecutionResponse(
        tool_name=request.tool_name,
        status=result.status,
        data=result.data,
        error=result.error,
        execution_time=result.execution_time,
    )


@router.get("/tools/categories", response_model=List[str])
@inject
async def get_tool_categories(
    tool_registry: ToolRegistry = Depends(Provide[Container.tool_registry]),
):
    """Get list of all tool categories"""
    tools = tool_registry.list_tools()
    categories = list(set(tool.category for tool in tools))
    return sorted(categories)
