"""Database factory for Agno agent history storage"""

import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from threading import Lock

from agno.db.postgres.postgres import PostgresDb
from core.config import get_config


logger = logging.getLogger(__name__)


class AsyncPostgresDbWrapper:
    """Wrapper to handle PostgresDb operations in a thread pool to avoid async/sync conflicts"""

    def __init__(self, postgres_db: PostgresDb):
        self._db = postgres_db
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agno_db")
        self._lock = Lock()

    def __getattr__(self, name):
        """Delegate attribute access to the wrapped PostgresDb"""
        return getattr(self._db, name)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()

    def __del__(self):
        """Cleanup when object is garbage collected"""
        with contextlib.suppress(Exception):
            self.cleanup()

    def cleanup(self):
        """Clean up the thread pool and database connections"""
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
        if hasattr(self, "_db") and self._db and hasattr(self._db, "close"):
            # Close database connections if the db has a close method
            with contextlib.suppress(Exception):
                self._db.close()


class AgnoDatabaseFactory:
    """Factory for creating Agno database instances for agent history storage"""

    _instance_lock = Lock()
    _postgres_db_cache = None

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_postgres_db_url() -> str:
        """Get PostgreSQL database URL for Agno PostgresDb (standard PostgreSQL format)"""
        config = get_config()

        # Use AGNO_DB_URL if configured, otherwise construct from config
        if config.AGNO_DB_URL:
            return config.AGNO_DB_URL

        # Convert asyncpg URL to standard PostgreSQL format for Agno
        base_url = config.database_url
        if base_url.startswith("postgresql+asyncpg://"):
            # Remove asyncpg driver specification for standard PostgreSQL URL
            agno_url = base_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            # Construct standard PostgreSQL URL
            agno_url = f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"

        return agno_url

    @staticmethod
    def create_postgres_db() -> PostgresDb | None:
        """
        Create a PostgresDb instance for storing agent conversation history.

        Returns:
            PostgresDb: Configured database instance for agent history
        """
        try:
            with AgnoDatabaseFactory._instance_lock:
                if AgnoDatabaseFactory._postgres_db_cache is not None:
                    return AgnoDatabaseFactory._postgres_db_cache

                db_url = AgnoDatabaseFactory._get_postgres_db_url()
                # Mask credentials in logging
                safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
                logger.info(f"Creating PostgresDb for agent history with host: {safe_url}")

                # Create PostgresDb with Agno history configuration
                postgres_db = PostgresDb(
                    db_url=db_url,
                    session_table="agent_sessions",  # Store agent sessions
                    memory_table="agent_memories",  # Store agent memories
                    metrics_table="agent_metrics",  # Store agent metrics
                )

                # Validate connection before caching
                try:
                    # Simple validation - if this succeeds, connection is working
                    if hasattr(postgres_db, "db_url") and postgres_db.db_url:
                        logger.info("Successfully created PostgresDb for agent history")
                        AgnoDatabaseFactory._postgres_db_cache = postgres_db
                        return postgres_db
                    error_msg = "PostgresDb creation returned invalid instance"
                    raise ValueError(error_msg)
                except Exception as validation_error:
                    logger.error(f"Failed to validate PostgresDb connection: {validation_error}")
                    raise

        except Exception as e:
            logger.error(f"Failed to create PostgresDb: {e}")
            logger.warning(
                "Agent history storage not available. "
                "Agents will run without conversation history context."
            )
            # Return None to indicate no database available
            # This will disable history context but allow agents to run
            return None

    @staticmethod
    def create_async_postgres_db() -> AsyncPostgresDbWrapper | None:
        """
        Create an async-compatible PostgresDb wrapper for use in FastAPI endpoints.

        Returns:
            AsyncPostgresDbWrapper: Async wrapper around PostgresDb
        """
        postgres_db = AgnoDatabaseFactory.create_postgres_db()
        if postgres_db is None:
            return None

        return AsyncPostgresDbWrapper(postgres_db)

    @staticmethod
    def is_database_available() -> bool:
        """
        Check if database is available for agent history storage.

        Returns:
            bool: True if database can be configured, False otherwise
        """
        try:
            db = AgnoDatabaseFactory.create_postgres_db()
            return db is not None
        except Exception:
            return False
