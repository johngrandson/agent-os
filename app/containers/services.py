from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Factory

from app.agents.services.agent_service import AgentService
from app.knowledge.services.knowledge_service import KnowledgeService

# Initialization services
from app.initialization.services.database_initializer import DatabaseInitializer
from app.initialization.services.event_system_initializer import EventSystemInitializer
from app.initialization.services.tool_system_initializer import ToolSystemInitializer
from app.initialization.services.agent_os_integrator import AgentOSIntegrator
from app.initialization.application_bootstrapper import ApplicationBootstrapper


class ServicesContainer(DeclarativeContainer):
    """Service factory providers for dependency injection"""

    # Domain service factories - actual dependencies injected by main container
    agent_service = Factory(AgentService)
    knowledge_service = Factory(KnowledgeService)

    # Initialization service factories
    database_initializer = Factory(DatabaseInitializer)
    event_system_initializer = Factory(EventSystemInitializer)
    tool_system_initializer = Factory(ToolSystemInitializer)
    agent_os_integrator = Factory(AgentOSIntegrator)

    # Application bootstrapper factory
    application_bootstrapper = Factory(ApplicationBootstrapper)
