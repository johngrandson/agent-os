"""
Tool loader for automatically registering built-in tools
"""

import logging
from app.tools.registry import ToolRegistry
from app.tools.builtin.web_search import WebSearchTool
from app.tools.builtin.text_processor import TextSummarizerTool, TextAnalyzerTool

logger = logging.getLogger(__name__)


async def load_builtin_tools(tool_registry: ToolRegistry):
    """Load and register all built-in tools"""

    builtin_tools = [
        WebSearchTool(),
        TextSummarizerTool(),
        TextAnalyzerTool(),
    ]

    for tool in builtin_tools:
        try:
            await tool_registry.register_tool(tool)
            logger.info(f"Loaded built-in tool: {tool.name}")
        except Exception as e:
            logger.error(f"Failed to load tool {tool.name}: {e}")

    logger.info(f"Loaded {len(builtin_tools)} built-in tools")


def get_available_tools(tool_registry: ToolRegistry):
    """Get list of all available tools with their definitions"""
    tools = tool_registry.list_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "definition": tool.get_definition().dict(),
        }
        for tool in tools
    ]
