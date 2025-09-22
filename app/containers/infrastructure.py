from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Singleton, ThreadSafeSingleton
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.events.bus import EventBus
from app.tools.registry import ToolRegistry
from app.integrations.services import IntegrationService
from core.config import get_config


class InfrastructureContainer(DeclarativeContainer):
    """Core infrastructure and external services"""

    # Database engines as simple singletons (Resource providers causing serialization issues)
    def _create_writer_engine():
        config_obj = get_config()
        return create_async_engine(
            config_obj.WRITER_DB_URL,
            pool_recycle=3600,
            echo=config_obj.DEBUG,
        )

    def _create_reader_engine():
        config_obj = get_config()
        return create_async_engine(
            config_obj.READER_DB_URL,
            pool_recycle=3600,
            echo=config_obj.DEBUG,
        )

    writer_engine = Singleton(_create_writer_engine)
    reader_engine = Singleton(_create_reader_engine)

    # Session factories
    writer_session_factory = Singleton(
        async_sessionmaker,
        bind=writer_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    reader_session_factory = Singleton(
        async_sessionmaker,
        bind=reader_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Configuration as singleton
    def _init_config():
        config_obj = get_config()
        return {
            "database": {
                "writer_url": config_obj.WRITER_DB_URL,
                "reader_url": config_obj.READER_DB_URL,
            },
            "openai": {
                "api_key": getattr(config_obj, "OPENAI_API_KEY", None),
            },
            "app": {
                "host": config_obj.APP_HOST,
                "port": config_obj.APP_PORT,
                "debug": config_obj.DEBUG,
                "env": config_obj.ENV,
            },
            "encryption": {
                "key": config_obj.ENCRYPTION_KEY,
            },
            "jwt": {
                "secret_key": config_obj.JWT_SECRET_KEY,
                "algorithm": config_obj.JWT_ALGORITHM,
            },
        }

    config_resource = Singleton(_init_config)

    # External clients - configuration will be set later
    openai_client = Singleton(AsyncOpenAI)

    # Core infrastructure with thread safety
    event_bus = ThreadSafeSingleton(EventBus)
    tool_registry = ThreadSafeSingleton(ToolRegistry, event_bus=event_bus)

    # Integration service
    integration_service = ThreadSafeSingleton(
        IntegrationService,
        event_bus=event_bus,
    )
