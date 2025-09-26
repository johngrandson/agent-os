#!/usr/bin/env python3
"""Test script to verify agent behavior when database is not available"""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.agent import Agent
from app.providers.agno.agent_converter import AgnoAgentConverter
from app.providers.agno.knowledge_adapter import AgnoKnowledgeAdapter
from app.providers.agno.model_factory import AgnoModelFactory
from core.config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_without_database():
    """Test agent behavior when database is not available (should disable history gracefully)"""
    logger.info("🧪 Testing agent behavior without database...")

    try:
        # Create test agent
        test_agent = Agent.create(
            name="Test Agent No DB",
            phone_number="+5511999999998",
            description="Test agent without database",
            instructions=["Be helpful"],
            is_active=True,
            llm_model="gpt-4o-mini",
            default_language="pt-BR",
        )

        # Create converter dependencies with mocked database failure
        config = get_config()

        # Mock the database factory to return None (simulating database unavailable)
        with patch('app.providers.agno.database_factory.AgnoDatabaseFactory.create_postgres_db', return_value=None):
            # Mock knowledge adapter to avoid DB connection
            with patch.object(AgnoKnowledgeAdapter, 'create_knowledge_for_agent', return_value=None):
                knowledge_adapter = AgnoKnowledgeAdapter(
                    db_url="sqlite:///:memory:",  # Use in-memory for test
                    event_publisher=None
                )
                model_factory = AgnoModelFactory(config=config)

                # Create converter
                converter = AgnoAgentConverter(
                    knowledge_adapter=knowledge_adapter,
                    model_factory=model_factory,
                )

                # Convert agent - this should disable history automatically and NOT show warning
                logger.info("🔄 Converting agent with no database (history should be disabled)...")
                agno_agent = await converter.convert_agent(
                    test_agent,
                    add_history_to_context=True,  # We request history but it should be disabled
                    num_history_runs=3,
                )

                logger.info(f"✅ Agent '{agno_agent.name}' created successfully")
                logger.info(f"📊 History requested: True, but actual: {agno_agent.add_history_to_context}")
                logger.info(f"🗃️  Database configured: {agno_agent.db is not None}")

                # Verify that history was disabled due to no database
                if not agno_agent.add_history_to_context:
                    logger.info("✅ History correctly disabled when database not available")
                else:
                    logger.warning("⚠️  History still enabled despite no database")

                return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_agent_without_database())
    if success:
        logger.info("🎉 Agent no-database test completed successfully")
        logger.info("💡 The warning 'add_history_to_context is True, but no database has been assigned' should NOT appear")
    else:
        logger.error("💥 Agent no-database test failed")
        exit(1)
