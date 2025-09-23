"""
Database initialization service
"""

import logging
import os
from dotenv import load_dotenv
from infrastructure.database import Base
from infrastructure.database.session import engines, EngineType

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization and model registration"""

    def __init__(self):
        self._ensure_environment_loaded()

    def _ensure_environment_loaded(self):
        """Ensure environment variables are loaded with local override"""
        if os.path.exists(".env.local"):
            load_dotenv(".env.local", override=True)
        else:
            load_dotenv(override=True)

    def _import_models(self):
        """Import all models to ensure they are registered with SQLAlchemy
        """
        from app.agents.agent import Agent

    async def initialize(self):
        """Initialize database tables"""
        try:
            # Import models to register them with SQLAlchemy
            self._import_models()

            async with engines[EngineType.WRITER].begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
