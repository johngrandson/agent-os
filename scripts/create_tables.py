#!/usr/bin/env python3
"""Create database tables script"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database import Base
from infrastructure.database.session import engines, EngineType


async def create_tables():
    """Create all database tables"""
    try:
        async with engines[EngineType.WRITER].begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_tables())
