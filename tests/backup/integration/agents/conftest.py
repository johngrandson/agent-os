"""Test fixtures for agent integration tests."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from app.agents.agent import Agent
from app.agents.api.schemas import CreateAgentCommand, UpdateAgentCommand
from app.agents.repositories.agent_repository import AgentRepository
from app.agents.services.agent_service import AgentService
from app.container import Container
from app.events.agents.publisher import AgentEventPublisher
from infrastructure.database import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def test_db_engine():
    """Create test database engine with in-memory SQLite."""
    # Use SQLite in-memory for fast tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def agent_repository(test_session) -> AgentRepository:
    """Create agent repository with test session."""
    # Set up session context for scoped session
    from infrastructure.database.session import reset_session_context, set_session_context

    # Set a test session context
    context = set_session_context("test-session")

    # Mock the get_session to return our test session
    import app.agents.repositories.agent_repository as repo_module

    original_get_session = repo_module.get_session

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_session():
        yield test_session

    repo_module.get_session = mock_get_session

    # Also need to mock the scoped session for transactional operations
    from infrastructure.database.session import session as original_scoped_session

    # Create a mock scoped session that uses our test session
    # This mock needs to behave like the real scoped session
    class MockScopedSession:
        def __init__(self, test_session):
            self._test_session = test_session

        async def commit(self):
            await self._test_session.commit()

        async def rollback(self):
            await self._test_session.rollback()

        # Add other methods that might be called
        def __call__(self):
            return self._test_session

        def remove(self):
            pass

        async def close(self):
            pass

    # Mock the scoped session at module level
    import infrastructure.database.session

    mock_scoped_session = MockScopedSession(test_session)
    infrastructure.database.session.session = mock_scoped_session

    # Also mock the transactional session for service tests
    import infrastructure.database.transactional

    infrastructure.database.transactional.session = mock_scoped_session

    repo = AgentRepository()

    yield repo

    # Restore original functions
    repo_module.get_session = original_get_session
    infrastructure.database.session.session = original_scoped_session

    # Reset context - ignore if context was created in different task
    try:
        reset_session_context(context)
    except ValueError:
        # Context was created in different task, ignore
        pass


@pytest.fixture
def mock_event_publisher() -> AgentEventPublisher:
    """Create mock event publisher."""
    mock_publisher = Mock(spec=AgentEventPublisher)
    mock_publisher.agent_created = AsyncMock()
    mock_publisher.agent_updated = AsyncMock()
    mock_publisher.agent_deleted = AsyncMock()
    return mock_publisher


@pytest.fixture
def agent_service(agent_repository, mock_event_publisher) -> AgentService:
    """Create agent service with mocked dependencies."""
    return AgentService(
        repository=agent_repository,
        event_publisher=mock_event_publisher,
    )


@pytest.fixture
def sample_agent_data() -> dict:
    """Sample agent data for testing."""
    return {
        "name": "Test Agent",
        "phone_number": "+5511999999999",
        "description": "A test agent for integration testing",
        "instructions": ["Be helpful", "Be polite"],
        "is_active": True,
        "llm_model": "gpt-4",
        "default_language": "pt-BR",
    }


@pytest.fixture
def create_agent_command(sample_agent_data) -> CreateAgentCommand:
    """Create agent command for testing."""
    return CreateAgentCommand(**sample_agent_data)


class AgentFactory:
    """Factory for creating test agents."""

    @staticmethod
    def build_agent(**kwargs) -> Agent:
        """Build an agent with default test data."""
        defaults = {
            "name": "Test Agent",
            "phone_number": f"+551199999{uuid.uuid4().hex[:4]}",
            "description": "Test agent description",
            "instructions": ["Test instruction 1", "Test instruction 2"],
            "is_active": True,
            "llm_model": "gpt-4",
            "default_language": "pt-BR",
        }
        defaults.update(kwargs)
        return Agent.create(**defaults)

    @staticmethod
    def build_agents(count: int, **kwargs) -> list[Agent]:
        """Build multiple agents with unique phone numbers."""
        agents = []
        for i in range(count):
            agent_kwargs = kwargs.copy()
            if "phone_number" not in agent_kwargs:
                agent_kwargs["phone_number"] = f"+55119999{i:04d}"
            if "name" not in agent_kwargs:
                agent_kwargs["name"] = f"Test Agent {i + 1}"
            agents.append(AgentFactory.build_agent(**agent_kwargs))
        return agents

    @staticmethod
    def build_create_command(**kwargs) -> CreateAgentCommand:
        """Build a create agent command."""
        defaults = {
            "name": "Test Agent",
            "phone_number": f"+551199999{uuid.uuid4().hex[:4]}",
            "description": "Test agent description",
            "instructions": ["Test instruction 1", "Test instruction 2"],
            "is_active": True,
            "llm_model": "gpt-4",
            "default_language": "pt-BR",
        }
        defaults.update(kwargs)
        return CreateAgentCommand(**defaults)

    @staticmethod
    def build_update_command(agent_id: str, **kwargs) -> UpdateAgentCommand:
        """Build an update agent command."""
        defaults = {
            "agent_id": agent_id,
            "name": "Updated Agent",
            "phone_number": f"+551199999{uuid.uuid4().hex[:4]}",
            "description": "Updated description",
            "instructions": ["Updated instruction"],
            "is_active": False,
            "llm_model": "gpt-3.5-turbo",
            "default_language": "en-US",
        }
        defaults.update(kwargs)
        return UpdateAgentCommand(**defaults)


@pytest.fixture
def agent_factory() -> AgentFactory:
    """Provide agent factory."""
    return AgentFactory


@pytest_asyncio.fixture
async def persisted_agent(agent_repository, agent_factory) -> Agent:
    """Create and persist an agent in the test database."""
    agent = agent_factory.build_agent()
    return await agent_repository.create_agent(agent=agent)


@pytest_asyncio.fixture
async def persisted_agents(agent_repository, agent_factory) -> list[Agent]:
    """Create and persist multiple agents in the test database."""
    agents = agent_factory.build_agents(3)
    persisted = []
    for agent in agents:
        persisted.append(await agent_repository.create_agent(agent=agent))
    return persisted


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def container_override():
    """Override container dependencies for testing."""
    container = Container()

    # Override with test configurations if needed
    yield container

    # Reset container
    container.reset_singletons()


# Custom markers for agent tests
def pytest_configure(config):
    """Configure custom pytest markers for agent tests."""
    config.addinivalue_line("markers", "agent_repository: Tests for agent repository layer")
    config.addinivalue_line("markers", "agent_service: Tests for agent service layer")
    config.addinivalue_line("markers", "agent_api: Tests for agent API endpoints")
    config.addinivalue_line("markers", "agent_integration: Integration tests for agents")
    config.addinivalue_line("markers", "database: Tests that require database")
    config.addinivalue_line("markers", "events: Tests for event publishing")
