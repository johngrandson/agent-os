"""
Startup module - Handles application initialization using dependency injection
"""

import logging

from app.container import Container
from dependency_injector.wiring import Provide, inject


logger = logging.getLogger(__name__)


class StartupManager:
    """Application startup manager using dependency injection"""

    @inject
    def __init__(self, bootstrapper=Provide[Container.application_bootstrapper]):
        self.bootstrapper = bootstrapper

    async def initialize_database(self):
        """Initialize database tables"""
        await self.bootstrapper.initialize_database()

    async def initialize_tools(self):
        """Initialize tool registry with built-in tools"""
        await self.bootstrapper.initialize_tools()

    async def initialize_event_system(self):
        """Initialize event bus and handlers"""
        await self.bootstrapper.initialize_event_system()

    def setup_agent_os_sync(self, fastapi_app):
        """Setup AgentOS synchronously after agents are loaded"""
        return self.bootstrapper.setup_agent_os(fastapi_app)
