#!/usr/bin/env python3
"""Test script to verify agent history configuration"""

import asyncio
import logging
import sys
from pathlib import Path

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


async def test_agent_with_history():
    """Test creating an agent with history context enabled"""
    logger.info("🧪 Testing agent with history configuration...")

    try:
        # Create test agent
        test_agent = Agent.create(
            name="Test Agent",
            phone_number="+5511999999999",
            description="Test agent for history verification",
            instructions=["Be helpful", "Be polite"],
            is_active=True,
            llm_model="gpt-4o-mini",
            default_language="pt-BR",
        )

        # Create converter dependencies
        config = get_config()
        knowledge_adapter = AgnoKnowledgeAdapter(
            db_url=config.WRITER_DB_URL,
            event_publisher=None
        )
        model_factory = AgnoModelFactory(config=config)

        # Create converter
        converter = AgnoAgentConverter(
            knowledge_adapter=knowledge_adapter,
            model_factory=model_factory,
        )

        # Convert agent (this should not produce the warning now)
        logger.info("🔄 Converting agent with history enabled...")
        agno_agent = await converter.convert_agent(
            test_agent,
            add_history_to_context=True,
            num_history_runs=3,
        )

        logger.info(f"✅ Agent '{agno_agent.name}' created successfully")
        logger.info(f"📊 History enabled: {agno_agent.add_history_to_context}")
        logger.info(f"🗃️  Database configured: {agno_agent.db is not None}")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_agent_with_history())
    if success:
        logger.info("🎉 Agent history test completed successfully")
    else:
        logger.error("💥 Agent history test failed")
        exit(1)
