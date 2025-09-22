"""
Tool registry for managing available agent tools
"""

import time
import logging
from typing import Dict, List, Optional
from app.tools.base import AgentTool, ToolResult, ToolStatus
from app.events.bus import EventBus
from app.tools.events import ToolEvent

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing and executing agent tools"""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.tools: Dict[str, AgentTool] = {}
        self.event_bus = event_bus

    async def register_tool(self, tool: AgentTool) -> None:
        """Register a new tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

        # Emit tool registration event
        if self.event_bus:
            await self.event_bus.emit(
                ToolEvent.tool_registered(
                    tool_name=tool.name,
                    data={
                        "category": tool.category,
                        "description": tool.description,
                    },
                )
            )

    async def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")

            # Emit tool unregistration event
            if self.event_bus:
                await self.event_bus.emit(
                    ToolEvent.tool_unregistered(
                        tool_name=tool_name,
                        data={
                            "category": tool.category,
                            "description": tool.description,
                        },
                    )
                )
            return True
        return False

    def get_tool(self, tool_name: str) -> Optional[AgentTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)

    def list_tools(self, category: Optional[str] = None) -> List[AgentTool]:
        """List all available tools, optionally filtered by category"""
        tools = list(self.tools.values())

        if category:
            tools = [tool for tool in tools if tool.category == category]

        return tools

    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self.tools.keys())

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """Execute a tool with the given parameters"""

        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR, error=f"Tool '{tool_name}' not found"
            )

        # Validate parameters
        if not tool.validate_parameters(parameters):
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid parameters for tool '{tool_name}'",
            )

        # Execute tool with timing
        start_time = time.time()
        try:
            result = await tool.execute(parameters)
            execution_time = time.time() - start_time
            result.execution_time = execution_time

            logger.info(
                f"Tool '{tool_name}' executed successfully in {execution_time:.2f}s"
            )

            # Emit successful tool execution event
            if self.event_bus:
                await self.event_bus.emit(
                    ToolEvent.tool_executed(
                        tool_name=tool_name,
                        results={
                            "execution_time": execution_time,
                            "status": result.status.value,
                            "data_size": len(str(result.data)) if result.data else 0,
                        },
                    )
                )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool '{tool_name}' failed: {str(e)}")

            # Emit failed tool execution event
            if self.event_bus:
                await self.event_bus.emit(
                    ToolEvent.tool_failed(tool_name=tool_name, error=str(e))
                )

            return ToolResult(
                status=ToolStatus.ERROR, error=str(e), execution_time=execution_time
            )


# Global tool registry instance - will be initialized with EventBus in container
tool_registry = None
