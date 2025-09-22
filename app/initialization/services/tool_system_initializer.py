"""
Tool system initialization service
"""

import logging
from app.tools.loader import load_builtin_tools
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolSystemInitializer:
    """Handles tool registry initialization with built-in tools"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    async def initialize(self):
        """Initialize tool registry with built-in tools"""
        try:
            await load_builtin_tools(self.tool_registry)
            logger.info("Tools initialized successfully")

        except Exception as e:
            logger.error(f"Tool system initialization failed: {e}")
            raise
