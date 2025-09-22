"""Test container with proper mocking support"""

from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Singleton
from unittest.mock import AsyncMock, MagicMock

from app.events.bus import EventBus
from app.tools.registry import ToolRegistry
from app.containers.infrastructure import InfrastructureContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.services import ServicesContainer


class TestContainer(DeclarativeContainer):
    """Test container with mocked dependencies"""

    # Mocked infrastructure
    openai_client = Singleton(AsyncMock)
    event_bus = Singleton(MagicMock, spec=EventBus)
    tool_registry = Singleton(MagicMock, spec=ToolRegistry)
    integration_service = Singleton(MagicMock)

    # Mocked session factories
    writer_session_factory = Singleton(AsyncMock)
    reader_session_factory = Singleton(AsyncMock)

    # Mocked repositories
    agent_repository = Singleton(MagicMock)
    knowledge_repository = Singleton(MagicMock)
    task_repository = Singleton(MagicMock)
    team_repository = Singleton(MagicMock)

    # Test services with mocked dependencies
    agent_service = Singleton(
        ServicesContainer.agent_service,
        repository=agent_repository,
        event_bus=event_bus,
        tool_registry=tool_registry,
    )

    knowledge_service = Singleton(
        ServicesContainer.knowledge_service,
        repository=knowledge_repository,
        openai_client=openai_client,
        event_bus=event_bus,
    )

    task_service = Singleton(
        ServicesContainer.task_service,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_bus=event_bus,
        tool_registry=tool_registry,
    )

    team_service = Singleton(
        ServicesContainer.team_service,
        team_repository=team_repository,
        event_bus=event_bus,
    )

    # Workflow services
    workflow_engine = Singleton(
        ServicesContainer.workflow_engine,
        event_bus=event_bus,
        task_service=task_service,
        integration_service=integration_service,
        agent_service=agent_service,
    )

    workflow_service = Singleton(
        ServicesContainer.workflow_service,
        workflow_engine=workflow_engine,
        event_bus=event_bus,
    )

    @classmethod
    def override_providers_for_test(cls, **overrides):
        """Helper method to override specific providers for testing"""
        container = cls()
        for provider_name, mock_value in overrides.items():
            if hasattr(container, provider_name):
                getattr(container, provider_name).override(mock_value)
        return container

    def reset_all_mocks(self):
        """Reset all mocked dependencies"""
        for provider_name in dir(self):
            provider = getattr(self, provider_name)
            if hasattr(provider, "provided") and hasattr(
                provider.provided, "reset_mock"
            ):
                provider.provided.reset_mock()
