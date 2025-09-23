from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import ThreadSafeSingleton

from app.containers.infrastructure import InfrastructureContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.services import ServicesContainer


class ApplicationContainer(DeclarativeContainer):
    """Main application container with proper dependency management"""

    wiring_config = WiringConfiguration(packages=["app", "app.initialization"])

    # Include sub-containers
    infrastructure = InfrastructureContainer()
    repositories = RepositoriesContainer()
    services = ServicesContainer()

    # Infrastructure services
    openai_client = infrastructure.openai_client
    event_bus = infrastructure.event_bus
    tool_registry = infrastructure.tool_registry
    config_resource = infrastructure.config_resource
    writer_engine = infrastructure.writer_engine
    reader_engine = infrastructure.reader_engine

    # Repositories
    agent_repository = repositories.agent_repository

    # Domain services with thread-safe dependency injection
    agent_service = ThreadSafeSingleton(
        services.agent_service,
        repository=agent_repository,
        event_bus=event_bus,
        tool_registry=tool_registry,
    )

    # Initialization services
    database_initializer = services.database_initializer

    event_system_initializer = ThreadSafeSingleton(
        services.event_system_initializer,
        agent_service=agent_service,
    )

    tool_system_initializer = ThreadSafeSingleton(
        services.tool_system_initializer,
        tool_registry=tool_registry,
    )

    agent_os_integrator = ThreadSafeSingleton(
        services.agent_os_integrator,
        agent_repository=agent_repository,
        event_bus=event_bus,
    )

    application_bootstrapper = ThreadSafeSingleton(
        services.application_bootstrapper,
        database_initializer=database_initializer,
        event_system_initializer=event_system_initializer,
        tool_system_initializer=tool_system_initializer,
        agent_os_integrator=agent_os_integrator,
    )
