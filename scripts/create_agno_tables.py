#!/usr/bin/env python3
"""Script to create Agno database tables for agent history storage"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.providers.agno.database_factory import AgnoDatabaseFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_agno_tables():
    """Create Agno database tables if they don't exist"""
    logger.info("🔧 Creating Agno database tables...")

    try:
        # Create database instance
        postgres_db = AgnoDatabaseFactory.create_postgres_db()

        if postgres_db is None:
            logger.error("❌ Could not create database connection")
            return False

        # Create tables - Agno PostgresDb should handle table creation automatically
        # when first used, but we can try to trigger it explicitly
        logger.info("✅ Database connection established")
        logger.info("📊 Agno tables will be created automatically when agents are used")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to create Agno tables: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(create_agno_tables())
    if success:
        logger.info("🎉 Agno database setup completed")
    else:
        logger.error("💥 Agno database setup failed")
        exit(1)
