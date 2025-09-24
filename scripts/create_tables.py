#!/usr/bin/env python3
"""Create database tables script"""

import asyncio
from pathlib import Path
import sys


# Add the project root to the path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from infrastructure.database import Base
from infrastructure.database.session import EngineType, engines


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
