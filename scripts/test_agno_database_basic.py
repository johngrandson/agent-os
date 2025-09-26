#!/usr/bin/env python3
"""Basic test to verify Agno database integration without complex dependencies"""

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


async def test_basic_agno_database():
    """Test basic Agno database integration"""
    logger.info("🧪 Testing basic Agno database integration...")

    try:
        # Create test agent
        test_agent = Agent.create(
            name="Test Agent Basic",
            phone_number="+5511999999997",
            description="Basic test agent",
            instructions=["Be helpful"],
            is_active=True,
            llm_model="gpt-4o-mini",
            default_language="pt-BR",
        )

        # Mock knowledge adapter to avoid database complexity
        with patch.object(AgnoKnowledgeAdapter, 'create_knowledge_for_agent', return_value=None):
            config = get_config()
            knowledge_adapter = AgnoKnowledgeAdapter(
                db_url=config.WRITER_DB_URL,
                event_publisher=None
            )
            model_factory = AgnoModelFactory(config=config)

            # Create converter - this should initialize the database
            converter = AgnoAgentConverter(
                knowledge_adapter=knowledge_adapter,
                model_factory=model_factory,
            )

            # Check if database was created
            if converter.db is not None:
                logger.info("✅ Database successfully initialized for agent history")
            else:
                logger.warning("⚠️  Database not available, history will be disabled")

            # Convert agent with history enabled
            logger.info("🔄 Converting agent with database available...")
            agno_agent = await converter.convert_agent(
                test_agent,
                add_history_to_context=True,
                num_history_runs=3,
            )

            logger.info(f"✅ Agent '{agno_agent.name}' created successfully")
            logger.info(f"📊 History enabled: {agno_agent.add_history_to_context}")
            logger.info(f"🗃️  Database assigned: {agno_agent.db is not None}")

            # Verify no warning about missing database
            if agno_agent.add_history_to_context and agno_agent.db is not None:
                logger.info("✅ No database warning - history properly configured!")
                return True
            else:
                logger.warning("⚠️  History not properly configured")
                return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_basic_agno_database())
    if success:
        logger.info("🎉 Basic Agno database test completed successfully")
        logger.info("💡 The warning about missing database should NOT appear")
    else:
        logger.error("💥 Basic Agno database test failed")
        exit(1)
