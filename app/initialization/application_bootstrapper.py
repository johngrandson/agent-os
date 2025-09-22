"""
Application bootstrapper - orchestrates initialization services
"""

import logging

logger = logging.getLogger(__name__)


class ApplicationBootstrapper:
    """Orchestrates application initialization using injected services"""

    def __init__(
        self,
        database_initializer,
        event_system_initializer,
        tool_system_initializer,
        agent_os_integrator,
    ):
        self.database_initializer = database_initializer
        self.event_system_initializer = event_system_initializer
        self.tool_system_initializer = tool_system_initializer
        self.agent_os_integrator = agent_os_integrator

    async def initialize_database(self):
        """Initialize database tables"""
        await self.database_initializer.initialize()

    async def initialize_tools(self):
        """Initialize tool registry with built-in tools"""
        await self.tool_system_initializer.initialize()

    async def initialize_event_system(self):
        """Initialize event system and load agents"""
        await self.event_system_initializer.initialize()
        # Load agents for the event system
        await self.agent_os_integrator.load_agents_for_event_system()

    def setup_agent_os(self, fastapi_app):
        """Setup AgentOS integration"""
        return self.agent_os_integrator.setup_with_app(fastapi_app)
