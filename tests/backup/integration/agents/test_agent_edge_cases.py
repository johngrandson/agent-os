"""Integration tests for agent edge cases and error scenarios.

These tests focus on boundary conditions, error handling,
and unusual scenarios that could occur in production.
"""

from unittest.mock import patch

import pytest
from app.agents.agent import Agent
from app.agents.repositories.agent_repository import AgentRepository
from app.agents.services.agent_service import AgentService
from sqlalchemy.exc import DatabaseError


@pytest.mark.asyncio
@pytest.mark.agent_integration
@pytest.mark.database
class TestAgentDatabaseConstraints:
    """Test database constraints and validation rules."""

    async def test_phone_number_unique_constraint_violation(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should raise integrity error for duplicate phone numbers."""
        # Arrange
        agent1 = agent_factory.build_agent(phone_number="+5511999999999")
        await agent_repository.create_agent(agent=agent1)

        agent2 = agent_factory.build_agent(phone_number="+5511999999999")  # Same phone

        # Act & Assert
        with pytest.raises(Exception):  # IntegrityError from database
            await agent_repository.create_agent(agent=agent2)

    async def test_agent_name_length_limits(self, agent_repository: AgentRepository, agent_factory):
        """Should handle agent names at database column limits."""
        # Arrange - Test with 255 characters (assumed limit from schema)
        long_name = "A" * 255
        agent = agent_factory.build_agent(name=long_name)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert created_agent.name == long_name
        assert len(created_agent.name) == 255

    async def test_agent_name_exceeding_limits(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle agent names exceeding database limits."""
        # Arrange - Test with 256 characters (over limit)
        very_long_name = "A" * 256
        agent = agent_factory.build_agent(name=very_long_name)

        # Act & Assert - Should raise database error
        with pytest.raises(Exception):
            await agent_repository.create_agent(agent=agent)

    async def test_phone_number_length_limits(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle phone numbers at database column limits."""
        # Arrange - Test with 255 characters
        long_phone = "+" + "1" * 254  # 255 total characters
        agent = agent_factory.build_agent(phone_number=long_phone)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert created_agent.phone_number == long_phone

    async def test_description_length_limits(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle descriptions at database column limits."""
        # Arrange - Test with 1000 characters (assumed limit)
        long_description = "A" * 1000
        agent = agent_factory.build_agent(description=long_description)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert created_agent.description == long_description
        assert len(created_agent.description) == 1000

    async def test_llm_model_length_limits(self, agent_repository: AgentRepository, agent_factory):
        """Should handle LLM model names at database column limits."""
        # Arrange - Test with 100 characters (assumed limit)
        long_model = "A" * 100
        agent = agent_factory.build_agent(llm_model=long_model)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert created_agent.llm_model == long_model

    async def test_default_language_length_limits(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle default language codes at limits."""
        # Arrange - Test with 10 characters (assumed limit)
        long_language = "A" * 10
        agent = agent_factory.build_agent(default_language=long_language)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert created_agent.default_language == long_language

    async def test_instructions_json_field_large_data(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle large instructions JSON arrays."""
        # Arrange - Create large list of instructions
        large_instructions = [f"Instruction {i}: " + "A" * 100 for i in range(1000)]
        agent = agent_factory.build_agent(instructions=large_instructions)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert len(created_agent.instructions) == 1000
        assert created_agent.instructions[0].startswith("Instruction 0:")
        assert created_agent.instructions[999].startswith("Instruction 999:")

    async def test_instructions_json_field_nested_data(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle complex nested data in instructions JSON field."""
        # Arrange - Create complex instruction data
        complex_instructions = [
            "Simple instruction",
            "Instruction with special chars: éñüíóá",
            "Instruction with numbers: 12345",
            "Instruction with symbols: @#$%^&*()",
            {"type": "complex", "data": [1, 2, 3]},  # This might not work depending on field type
        ]

        # Note: This test assumes instructions field accepts strings only
        # If it accepts complex JSON, this would test that functionality
        string_instructions = [str(instr) for instr in complex_instructions]
        agent = agent_factory.build_agent(instructions=string_instructions)

        # Act
        created_agent = await agent_repository.create_agent(agent=agent)

        # Assert
        assert len(created_agent.instructions) == 5
        assert "éñüíóá" in created_agent.instructions[1]


@pytest.mark.asyncio
@pytest.mark.agent_integration
class TestAgentServiceErrorHandling:
    """Test error handling in service layer."""

    async def test_create_agent_handles_repository_database_error(
        self, agent_service: AgentService, agent_factory, mock_event_publisher
    ):
        """Should handle database errors from repository layer."""
        # Arrange
        command = agent_factory.build_create_command()

        # Mock repository to raise database error
        with patch.object(agent_service.repository, "create_agent") as mock_create:
            mock_create.side_effect = DatabaseError("Database connection failed", None, None)

            # Act & Assert
            with pytest.raises(DatabaseError):
                await agent_service.create_agent(command=command)

            # Event should not be published if database operation fails
            mock_event_publisher.agent_created.assert_not_called()

    async def test_update_agent_handles_repository_errors(
        self, agent_service: AgentService, agent_factory, persisted_agent: Agent
    ):
        """Should handle repository errors during update."""
        # Arrange
        command = agent_factory.build_update_command(agent_id=str(persisted_agent.id))

        # Mock repository to raise error on update
        with patch.object(agent_service.repository, "update_agent") as mock_update:
            mock_update.side_effect = DatabaseError("Update failed", None, None)

            # Act & Assert
            with pytest.raises(DatabaseError):
                await agent_service.update_agent(command=command)

    async def test_delete_agent_handles_repository_errors(
        self, agent_service: AgentService, persisted_agent: Agent
    ):
        """Should handle repository errors during delete."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Mock repository to raise error on delete
        with patch.object(agent_service.repository, "delete_agent") as mock_delete:
            mock_delete.side_effect = DatabaseError("Delete failed", None, None)

            # Act & Assert
            with pytest.raises(DatabaseError):
                await agent_service.delete_agent(agent_id=agent_id)

    async def test_service_handles_invalid_uuid_formats(self, agent_service: AgentService):
        """Should handle various invalid UUID formats gracefully."""
        invalid_uuids = [
            "",
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "123e4567-e89b-12d3-a456-42661417400",  # Missing character
            "123e4567-e89b-12d3-a456-4266141740000",  # Extra character
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError, match="Invalid UUID|UUID"):
                await agent_service.get_agent_by_id(agent_id=invalid_uuid)

    async def test_service_handles_event_publishing_failures(
        self, agent_service: AgentService, agent_factory, mock_event_publisher
    ):
        """Should handle event publishing failures appropriately."""
        # Arrange
        command = agent_factory.build_create_command()

        # Mock event publisher to fail
        mock_event_publisher.agent_created.side_effect = Exception("Event broker unavailable")

        # Act & Assert - This should fail due to the @Transactional decorator
        with pytest.raises(Exception, match="Event broker unavailable"):
            await agent_service.create_agent(command=command)


@pytest.mark.asyncio
@pytest.mark.agent_integration
class TestAgentRepositoryEdgeCases:
    """Test edge cases in repository layer."""

    async def test_pagination_with_zero_results(self, agent_repository: AgentRepository):
        """Should handle pagination when no results exist."""
        # Act
        agents = await agent_repository.get_agents(limit=10)

        # Assert
        assert isinstance(agents, list)
        assert len(agents) == 0

    async def test_pagination_with_prev_parameter_edge_cases(
        self, agent_repository: AgentRepository, persisted_agents: list[Agent]
    ):
        """Should handle edge cases with prev parameter."""
        # Test with very large prev value
        agents = await agent_repository.get_agents(limit=5, prev=999999999)
        assert isinstance(agents, list)

        # Test with very small prev value
        agents = await agent_repository.get_agents(limit=5, prev=0)
        assert isinstance(agents, list)

    async def test_get_agents_by_status_with_no_matches(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle status filter with no matching agents."""
        # Arrange - Create only active agents
        active_agents = agent_factory.build_agents(2, is_active=True)
        for agent in active_agents:
            await agent_repository.create_agent(agent=agent)

        # Act - Search for inactive agents
        inactive_agents = await agent_repository.get_agents_by_status(status=False, limit=10)

        # Assert
        assert isinstance(inactive_agents, list)
        assert len(inactive_agents) == 0

    async def test_update_agent_with_same_data(
        self, agent_repository: AgentRepository, persisted_agent: Agent
    ):
        """Should handle update with identical data."""
        # Arrange - Don't change any data
        original_updated_at = persisted_agent.updated_at

        # Act
        updated_agent = await agent_repository.update_agent(agent=persisted_agent)

        # Assert - Should succeed and potentially update timestamp
        assert updated_agent.id == persisted_agent.id
        assert updated_agent.name == persisted_agent.name
        # updated_at might change even with same data due to database behavior

    async def test_delete_already_deleted_agent(
        self, agent_repository: AgentRepository, persisted_agent: Agent
    ):
        """Should handle deleting an already deleted agent."""
        # Arrange - Delete the agent first
        await agent_repository.delete_agent(agent=persisted_agent)

        # Act & Assert - Second delete might raise an error or be idempotent
        # This behavior depends on the SQLAlchemy configuration
        try:
            await agent_repository.delete_agent(agent=persisted_agent)
        except Exception as e:
            # Some databases/ORMs might raise an error for deleting non-existent records
            assert e is not None


@pytest.mark.asyncio
@pytest.mark.agent_integration
class TestAgentSpecialCharacters:
    """Test handling of special characters and internationalization."""

    async def test_agent_with_unicode_characters(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle Unicode characters in all text fields."""
        # Arrange
        unicode_agent = agent_factory.build_agent(
            name="Agent 测试 🤖 José María",
            description="Descrição com acentos: àáâãäåæçèéêë",
            instructions=[
                "Instrução em português: ção, não, São Paulo",
                "中文指令：你好世界",
                "Русские инструкции: Привет мир",
                "العربية: مرحبا بالعالم",
                "Emoji instructions: 😀 😃 😄 😁 🎉 🔥 💯",
            ],
            llm_model="gpt-4-测试",
            default_language="pt-BR",
        )

        # Act
        created_agent = await agent_repository.create_agent(agent=unicode_agent)

        # Assert
        assert "测试" in created_agent.name
        assert "🤖" in created_agent.name
        assert "José María" in created_agent.name
        assert "àáâãäåæçèéêë" in created_agent.description
        assert "你好世界" in created_agent.instructions[1]
        assert "Привет мир" in created_agent.instructions[2]
        assert "مرحبا بالعالم" in created_agent.instructions[3]
        assert "😀 😃 😄" in created_agent.instructions[4]

    async def test_agent_with_special_phone_number_formats(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle various phone number formats."""
        phone_formats = [
            "+55 11 99999-9999",
            "+55-11-99999-9998",
            "+55.11.99999.9997",
            "+55 (11) 99999-9996",
            "55 11 999999995",
            "+1-800-555-0194",
            "+44 20 7946 0093",
            "+33 1 42 86 83 92",
            "+49 30 12345691",
        ]

        created_agents = []
        for i, phone_format in enumerate(phone_formats):
            agent = agent_factory.build_agent(name=f"Agent {i}", phone_number=phone_format)
            created_agent = await agent_repository.create_agent(agent=agent)
            created_agents.append(created_agent)

            # Verify phone number was stored correctly
            assert created_agent.phone_number == phone_format

    async def test_agent_with_json_characters_in_text_fields(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle JSON special characters in text fields."""
        # Arrange
        json_chars_agent = agent_factory.build_agent(
            name='Agent "JSON" Test',
            description='Description with {curly: "braces"} and [square, "brackets"]',
            instructions=[
                'Instruction with "quotes" and \\backslashes\\',
                "Instruction with 'single quotes' and \"double quotes\"",
                "Instruction with newlines\nand\ttabs",
                "Instruction with null\0characters",
            ],
        )

        # Act
        created_agent = await agent_repository.create_agent(agent=json_chars_agent)

        # Assert
        assert '"JSON"' in created_agent.name
        assert '{curly: "braces"}' in created_agent.description
        assert "\\backslashes\\" in created_agent.instructions[0]
        assert "single quotes" in created_agent.instructions[1]


@pytest.mark.asyncio
@pytest.mark.agent_integration
class TestAgentConcurrencyAndRaceConditions:
    """Test concurrent operations and race conditions."""

    async def test_concurrent_agent_creation_with_same_phone(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle concurrent creation attempts with same phone number."""
        import asyncio

        # Arrange
        phone_number = "+5511999999999"
        agents = [
            agent_factory.build_agent(name=f"Agent {i}", phone_number=phone_number)
            for i in range(3)
        ]

        # Act - Try to create agents concurrently
        tasks = [agent_repository.create_agent(agent=agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - Only one should succeed, others should raise exceptions
        successful_creates = [r for r in results if isinstance(r, Agent)]
        failed_creates = [r for r in results if isinstance(r, Exception)]

        assert len(successful_creates) == 1  # Only one should succeed
        assert len(failed_creates) == 2  # Two should fail due to unique constraint

    async def test_concurrent_updates_of_same_agent(
        self, agent_repository: AgentRepository, persisted_agent: Agent
    ):
        """Should handle concurrent updates of the same agent."""
        import asyncio

        # Arrange - Create multiple versions of the agent with different updates
        agent_updates = []
        for i in range(3):
            updated_agent = Agent.create(
                name=f"Updated Name {i}",
                phone_number=persisted_agent.phone_number,
                is_active=persisted_agent.is_active,
            )
            updated_agent.id = persisted_agent.id
            agent_updates.append(updated_agent)

        # Act - Try to update concurrently
        tasks = [agent_repository.update_agent(agent=agent) for agent in agent_updates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - All updates should succeed (last one wins)
        successful_updates = [r for r in results if isinstance(r, Agent)]
        assert len(successful_updates) >= 1  # At least one should succeed

        # Verify final state
        final_agent = await agent_repository.get_agent_by_id(agent_id=persisted_agent.id)
        assert final_agent is not None
        assert "Updated Name" in final_agent.name

    async def test_read_during_write_operations(
        self, agent_repository: AgentRepository, agent_factory
    ):
        """Should handle read operations during write operations."""
        import asyncio

        # Arrange
        agent = agent_factory.build_agent()
        created_agent = await agent_repository.create_agent(agent=agent)

        # Act - Perform concurrent read and update operations
        async def update_agent():
            created_agent.name = "Updated Name"
            return await agent_repository.update_agent(agent=created_agent)

        async def read_agent():
            return await agent_repository.get_agent_by_id(agent_id=created_agent.id)

        # Run operations concurrently
        update_task = asyncio.create_task(update_agent())
        read_task = asyncio.create_task(read_agent())

        update_result, read_result = await asyncio.gather(update_task, read_task)

        # Assert - Both operations should complete successfully
        assert isinstance(update_result, Agent)
        assert isinstance(read_result, Agent)
        assert read_result.id == created_agent.id
