#!/usr/bin/env python3
"""
Database Setup Script for Agent OS
Executes all migrations and sets up the database from scratch.
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_alembic_command(command: list[str]) -> bool:
    """Run an alembic command and return success status"""
    try:
        logger.info(f"Running: {' '.join(command)}")
        result = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"✅ Command successful: {' '.join(command)}")
        if result.stdout:
            logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Command failed: {' '.join(command)}")
        logger.error(f"Error: {e.stderr}")
        return False


async def setup_database() -> bool:
    """Setup database from scratch"""
    logger.info("🚀 Starting database setup...")

    # Check if we're in a Poetry environment
    poetry_commands = [
        ["poetry", "run", "alembic", "upgrade", "head"]
    ]

    direct_commands = [
        ["alembic", "upgrade", "head"]
    ]

    # Try Poetry first, then direct alembic
    commands_to_try = [poetry_commands, direct_commands]

    for command_set in commands_to_try:
        logger.info("Attempting to run migrations...")
        success = True

        for command in command_set:
            if not run_alembic_command(command):
                success = False
                break

        if success:
            logger.info("✅ Database setup completed successfully!")
            logger.info("\nDatabase is ready with:")
            logger.info("- PostgreSQL extensions (uuid-ossp, vector)")
            logger.info("- AI schema for Agno integration")
            logger.info("- Agents table with all fields")
            logger.info("- Indexes and triggers for performance")
            return True

        logger.warning("Failed with this approach, trying next...")

    logger.error("❌ All setup approaches failed!")
    sys.exit(1)


def show_current_status() -> None:
    """Show current migration status"""
    logger.info("📊 Current migration status:")
    run_alembic_command(["poetry", "run", "alembic", "current"])
    run_alembic_command(["poetry", "run", "alembic", "history", "--verbose"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup Agent OS Database")
    parser.add_argument("--status", action="store_true", help="Show current migration status")
    parser.add_argument("--reset", action="store_true", help="Reset database before setup (DANGEROUS)")

    args = parser.parse_args()

    if args.status:
        show_current_status()
    elif args.reset:
        logger.warning("⚠️  Reset functionality should be implemented with caution")
        logger.warning("⚠️  Please use Docker containers or manual DB reset for now")
    else:
        asyncio.run(setup_database())
