from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Singleton, ThreadSafeSingleton

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
    integration_service = infrastructure.integration_service
    config_resource = infrastructure.config_resource
    writer_engine = infrastructure.writer_engine
    reader_engine = infrastructure.reader_engine

    # Repositories
    agent_repository = repositories.agent_repository
    knowledge_repository = repositories.knowledge_repository
    task_repository = repositories.task_repository
    team_repository = repositories.team_repository

    # Domain services with thread-safe dependency injection
    agent_service = ThreadSafeSingleton(
        services.agent_service,
        repository=agent_repository,
        event_bus=event_bus,
        tool_registry=tool_registry,
    )

    knowledge_service = ThreadSafeSingleton(
        services.knowledge_service,
        repository=knowledge_repository,
        openai_client=openai_client,
        event_bus=event_bus,
    )

    task_service = ThreadSafeSingleton(
        services.task_service,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_bus=event_bus,
        tool_registry=tool_registry,
    )

    team_service = ThreadSafeSingleton(
        services.team_service,
        team_repository=team_repository,
        event_bus=event_bus,
    )

    # Workflow services with thread safety
    workflow_engine = ThreadSafeSingleton(
        services.workflow_engine,
        event_bus=event_bus,
        task_service=task_service,
        integration_service=integration_service,
        agent_service=agent_service,
    )

    workflow_service = ThreadSafeSingleton(
        services.workflow_service,
        workflow_engine=workflow_engine,
        event_bus=event_bus,
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
    )

    application_bootstrapper = ThreadSafeSingleton(
        services.application_bootstrapper,
        database_initializer=database_initializer,
        event_system_initializer=event_system_initializer,
        tool_system_initializer=tool_system_initializer,
        agent_os_integrator=agent_os_integrator,
    )
