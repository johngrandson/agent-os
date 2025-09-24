import redis.asyncio as redis
from app.agents.repositories.agent_repository import AgentRepository
from app.agents.services.agent_service import AgentService
from app.events.agents.publisher import AgentEventPublisher

# Application imports
from app.events.broker import broker
from app.events.webhooks.publisher import WebhookEventPublisher
from app.initialization.application_bootstrapper import ApplicationBootstrapper
from app.initialization.services.agent_os_initializer import AgentOSInitializer
from app.initialization.services.database_initializer import DatabaseInitializer
from app.initialization.services.event_system_initializer import EventSystemInitializer

# Agno integration imports
from app.integrations.agno import AgnoAgentConverter, AgnoKnowledgeAdapter, AgnoModelFactory
from app.webhook.services.webhook_agent_processor import WebhookAgentProcessor

# Core imports
from core.config import get_config
from dependency_injector import containers, providers
from dependency_injector.containers import WiringConfiguration
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Container(containers.DeclarativeContainer):
    """Simplified application container following dependency-injector best practices"""

    # Configuration
    config = providers.Configuration()

    # Wiring configuration - will be done manually to avoid circular imports
    # wiring_config = WiringConfiguration(packages=["app"])

    # Configuration provider
    config_object = providers.Singleton(get_config)

    # Database engines
    writer_engine = providers.Singleton(
        create_async_engine,
        config_object.provided.WRITER_DB_URL,
        pool_recycle=3600,
        echo=config_object.provided.DEBUG,
    )

    reader_engine = providers.Singleton(
        create_async_engine,
        config_object.provided.READER_DB_URL,
        pool_recycle=3600,
        echo=config_object.provided.DEBUG,
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

    # Services
    agent_service = providers.Singleton(
        AgentService,
        repository=agent_repository,
        event_publisher=agent_event_publisher,
    )

    # Webhook services
    webhook_agent_processor = providers.Factory(
        WebhookAgentProcessor,
        agent_repository=agent_repository,
        event_publisher=webhook_event_publisher,
        agno_agent_converter=agno_agent_converter,
    )

    # Initialization services
    database_initializer = providers.Factory(DatabaseInitializer)

    event_system_initializer = providers.Factory(
        EventSystemInitializer,
        agent_service=agent_service,
        event_publisher=agent_event_publisher,
    )

    agent_os_initializer = providers.Factory(
        AgentOSInitializer,
        agent_repository=agent_repository,
        event_publisher=agent_event_publisher,
        agno_agent_converter=agno_agent_converter,
    )

    application_bootstrapper = providers.Factory(
        ApplicationBootstrapper,
        database_initializer=database_initializer,
        event_system_initializer=event_system_initializer,
        agent_os_initializer=agent_os_initializer,
        webhook_agent_processor=webhook_agent_processor,
    )


# Container will be instantiated by the application
