#!/usr/bin/env python3
"""
Agent seeder to create comprehensive agents with detailed instructions
"""

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any


# Add project root to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from app.container import Container
from app.domains.agent_management.agent import Agent
from app.domains.agent_management.api.schemas import CreateAgentRequest
from infrastructure.database import Base
from infrastructure.database.session import reset_session_context, set_session_context


class AgentSeeder:
    def __init__(self) -> None:
        print("🔧 Initializing AgentSeeder...")
        try:
            self.container = Container()
            print("✅ Dependency container created")

            self.agent_service = self.container.agent_service()
            print("✅ Agent service loaded")

        except Exception as e:
            print(f"❌ Initialization error: {type(e).__name__}")
            print(f"   📋 Details: {e!s}")
            import traceback

            traceback.print_exc()
            raise

    async def create_tables(self) -> None:
        """Create tables if they don't exist"""
        # Use container to get the engine
        from core.config import get_config
        from sqlalchemy.ext.asyncio import create_async_engine

        config = get_config()
        engine = create_async_engine(config.writer_db_url)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await engine.dispose()

    async def seed_agents(self) -> list[Agent]:
        """Create comprehensive agents with detailed instructions"""
        agents_data: list[dict[str, Any]] = [
            {
                "name": "Dental Clinic Assistant",
                "phone_number": "+5511999999001",
                "description": "Professional dental clinic assistant for appointments and patient inquiries",
                "instructions": [
                    "Always respond with short, direct messages",
                    "Never assume information not explicitly provided",
                    "Ask for specific details when needed (full name, preferred date/time)",
                    "Confirm all appointment details before booking",
                    "Be professional and empathetic in all interactions",
                    "Only provide information about services actually offered",
                    "Request patient phone number for appointment confirmations",
                    "Explain procedures clearly using simple, non-technical language",
                    "Always offer alternative dates if requested time is unavailable",
                    "End conversations with clear next steps for the patient",
                ],
                "is_active": True,
            },
            {
                "name": "Customer Support Agent",
                "phone_number": "+5511999999002",
                "description": "Comprehensive customer support agent for general inquiries and problem resolution",
                "instructions": [
                    "Respond concisely and directly to customer questions",
                    "Never make assumptions about customer needs or technical knowledge",
                    "Ask clarifying questions to understand the specific issue",
                    "Provide step-by-step solutions when troubleshooting",
                    "Maintain a helpful and patient tone throughout the conversation",
                    "Only offer solutions and services that are actually available",
                    "Escalate complex technical issues to appropriate specialists",
                    "Confirm customer understanding before ending the conversation",
                    "Document important details for follow-up if needed",
                    "Always thank customers for their patience and business",
                ],
                "is_active": True,
            },
            {
                "name": "Sales Assistant",
                "phone_number": "+5511999999003",
                "description": "Professional sales assistant for product information and purchase guidance",
                "instructions": [
                    "Provide clear, accurate product information without overselling",
                    "Never assume customer budget or purchasing timeline",
                    "Ask about specific needs and use cases before recommending products",
                    "Present options with honest pros and cons",
                    "Be transparent about pricing, availability, and delivery times",
                    "Focus on matching products to actual customer requirements",
                    "Offer alternatives when preferred items are unavailable",
                    "Explain return policies and warranties clearly",
                    "Respect customer decisions without being pushy",
                    "Provide clear next steps for purchase completion",
                ],
                "is_active": True,
            },
        ]

        created_agents = []
        for agent_data in agents_data:
            try:
                # Create request for the service
                # Use Pydantic v2 parsing to avoid mypy named-argument warnings with dict expansion
                request = CreateAgentRequest.model_validate(agent_data)

                # Try to create the agent - will error if already exists
                agent = await self.agent_service.create_agent(request=request)
                created_agents.append(agent)
                status = "✅ ACTIVE" if agent.is_active else "⏸️  INACTIVE"
                print(f"✨ Created: {agent.name} ({agent.phone_number}) - {status}")
            except Exception as e:
                # Detailed error logging
                error_type = type(e).__name__
                error_message = str(e)

                # If agent already exists error, not critical
                if (
                    "AgentAlreadyExists" in error_type
                    or "already exists" in error_message.lower()
                ):
                    print(f"⚠️ Agent {agent_data['name']} already exists (phone: {agent_data['phone_number']})")
                    print(f"📋 Details: {error_type} - {error_message}")
                else:
                    print(f"❌ Error creating agent {agent_data['name']}: {error_type}")
                    print(f"📋 Details: {error_message}")
                    print(f"🔍 Error type: {error_type}")
                    # Traceback log for debugging
                    import traceback

                    print("   📊 Stack trace:")
                    traceback.print_exc()

        return created_agents

    async def run(self) -> None:
        """Execute the seeder"""

        try:
            session_id = str(uuid.uuid4())
            print(f"🔧 Configuring session with ID: {session_id}")
            context_token = set_session_context(session_id)
            print("✅ Session context configured")

            try:
                await self.create_tables()
                print("✅ Tables verified/created")

                agents = await self.seed_agents()
                print(f"✅ {len(agents)} agents created")

                # If no agents were created (already exist), fetch from database
                if not agents:
                    print("🔍 Searching for existing agents in database...")
                    existing_agents = await self.agent_service.get_agent_list(limit=100)
                    agents = existing_agents
                    print(f"✅ {len(agents)} agents found in database")

                print("🎉 Seeder executed successfully!")

            finally:
                # Clean up context
                reset_session_context(context_token)

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            print(f"❌ Error during seeder execution: {error_type}")
            print(f"   📋 Details: {error_message}")
            import traceback

            print("   📊 Complete stack trace:")
            traceback.print_exc()
            raise


async def main() -> None:
    """Main function"""
    seeder = AgentSeeder()
    await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())
