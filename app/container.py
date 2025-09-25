import redis.asyncio as redis
from app.agents.repositories.agent_repository import AgentRepository
from app.agents.services.agent_service import AgentService
from app.agents.services.orchestration_service import OrchestrationService
from app.events.agents.publisher import AgentEventPublisher

# Application imports
from app.events.broker import broker
from app.events.orchestration.publisher import OrchestrationEventPublisher
from app.events.orchestration.task_registry import TaskRegistry
from app.events.webhooks.publisher import WebhookEventPublisher
from app.initialization import AgentCache

# Agno integration imports
from app.integrations.agno import AgnoAgentConverter, AgnoKnowledgeAdapter, AgnoModelFactory
from app.webhook.services.webhook_agent_processor import WebhookAgentProcessor

# Core imports
from core.config import get_config
from dependency_injector import containers, providers
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import QueuePool


class Container(containers.DeclarativeContainer):
    """Application container following dependency-injector best practices"""

    # Configuration
    config = providers.Configuration()

    # Configuration provider
    config_object = providers.Singleton(get_config)

    # Database engines
    writer_engine = providers.Singleton(
        create_async_engine,
        config_object.provided.WRITER_DB_URL,
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=config_object.provided.DEBUG,
        poolclass=QueuePool,
    )

    reader_engine = providers.Singleton(
        create_async_engine,
        config_object.provided.READER_DB_URL,
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_size=20,  # Number of connections to keep in the pool
        pool_pre_ping=True,  # Test connections before using them
        max_overflow=30,  # Additional connections when needed
        echo=config_object.provided.DEBUG,
        poolclass=QueuePool,
    )

    # Session factories
    writer_session_factory = providers.Singleton(
        async_sessionmaker,
        bind=writer_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    reader_session_factory = providers.Singleton(
        async_sessionmaker,
        bind=reader_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Redis client
    redis_client = providers.Singleton(
        redis.from_url,
        config_object.provided.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # Event publishers - domain-specific
    agent_event_publisher = providers.Singleton(
        AgentEventPublisher,
        broker=broker,
    )

    webhook_event_publisher = providers.Singleton(
        WebhookEventPublisher,
        broker=broker,
    )

    orchestration_event_publisher = providers.Singleton(
        OrchestrationEventPublisher,
        broker=broker,
    )

    # OpenAI client
    openai_client = providers.Singleton(AsyncOpenAI)

    # Agno integration services
    agno_model_factory = providers.Singleton(
        AgnoModelFactory,
        config=config_object,
    )

    agno_knowledge_adapter = providers.Singleton(
        AgnoKnowledgeAdapter,
        db_url=config_object.provided.AGNO_DB_URL,
        event_publisher=agent_event_publisher,
    )

    agno_agent_converter = providers.Singleton(
        AgnoAgentConverter,
        knowledge_adapter=agno_knowledge_adapter,
        model_factory=agno_model_factory,
    )

    # Repositories
    agent_repository = providers.Factory(AgentRepository)

    # Orchestration components
    task_registry = providers.Singleton(TaskRegistry)

    # Services
    agent_service = providers.Singleton(
        AgentService,
        repository=agent_repository,
        event_publisher=agent_event_publisher,
    )

    orchestration_service = providers.Singleton(
        OrchestrationService,
        task_registry=task_registry,
        event_publisher=orchestration_event_publisher,
    )

    # Agent cache for simple storage and lookup
    agent_cache = providers.Singleton(
        AgentCache,
        agent_repository=agent_repository,
        agno_agent_converter=agno_agent_converter,
    )

    # Webhook services
    webhook_agent_processor = providers.Factory(
        WebhookAgentProcessor,
        agent_cache=agent_cache,
        event_publisher=webhook_event_publisher,
    )


# Container will be instantiated by the application
