import redis.asyncio as redis
from app.domains.agent_management.events.publisher import AgentEventPublisher
from app.domains.agent_management.repositories.agent_repository import AgentRepository
from app.domains.agent_management.services.agent_service import AgentService
from app.domains.communication.messages.publisher import MessageEventPublisher
from app.domains.communication.webhooks.services.webhook_agent_processor import (
    WebhookAgentProcessor,
)

# Provider imports
from app.infrastructure.providers.factory import get_provider

# Application imports
from app.initialization import AgentCache

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

    # Event broker - use a factory to return the singleton instance
    @providers.Factory
    def event_broker(self) -> object:
        """Return the singleton broker instance"""
        from app.shared.events.broker import broker

        return broker

    # Event publishers - domain-specific
    agent_event_publisher = providers.Singleton(
        AgentEventPublisher,
        broker=event_broker,
    )

    message_event_publisher = providers.Singleton(
        MessageEventPublisher,
        broker=event_broker,
    )

    # OpenAI client
    openai_client = providers.Singleton(AsyncOpenAI)

    # Agent provider factory
    agent_provider = providers.Singleton(get_provider)

    # Repositories
    agent_repository = providers.Factory(AgentRepository)

    # Services
    agent_service = providers.Singleton(
        AgentService,
        repository=agent_repository,
        event_publisher=agent_event_publisher,
    )

    # Agent cache for simple storage and lookup
    agent_cache = providers.Singleton(
        AgentCache,
        agent_repository=agent_repository,
        agent_provider=agent_provider,
    )

    # Webhook services
    webhook_agent_processor = providers.Factory(
        WebhookAgentProcessor,
        agent_cache=agent_cache,
        event_publisher=message_event_publisher,
    )


# Container will be instantiated by the application
