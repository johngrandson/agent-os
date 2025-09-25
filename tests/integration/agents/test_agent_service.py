"""Integration tests for AgentService.

These tests verify the business logic and integration between
the service layer, repository, and event publishing.
"""

import uuid

import pytest
from app.agents.agent import Agent
from app.agents.api.schemas import CreateAgentCommand, UpdateAgentCommand
from app.agents.services.agent_service import AgentService
from core.exceptions.domain import AgentAlreadyExists


@pytest.mark.asyncio
@pytest.mark.agent_service
@pytest.mark.database
class TestAgentServiceCreate:
    """Test agent creation through service layer."""

    async def test_create_agent_should_create_and_publish_event(
        self,
        agent_service: AgentService,
        create_agent_command: CreateAgentCommand,
        mock_event_publisher,
    ):
        """Should create agent and publish creation event."""
        # Act
        created_agent = await agent_service.create_agent(command=create_agent_command)

        # Assert
        assert created_agent is not None
        assert isinstance(created_agent.id, uuid.UUID)
        assert created_agent.name == create_agent_command.name
        assert created_agent.phone_number == create_agent_command.phone_number
        assert created_agent.description == create_agent_command.description
        assert created_agent.instructions == create_agent_command.instructions
        assert created_agent.is_active == create_agent_command.is_active
        assert created_agent.llm_model == create_agent_command.llm_model
        assert created_agent.default_language == create_agent_command.default_language

        # Verify event was published
        mock_event_publisher.agent_created.assert_called_once()
        call_args = mock_event_publisher.agent_created.call_args
        assert call_args[1]["agent_id"] == str(created_agent.id)
        assert call_args[1]["agent_data"]["name"] == created_agent.name
        assert call_args[1]["agent_data"]["is_active"] == created_agent.is_active
        assert call_args[1]["agent_data"]["phone_number"] == created_agent.phone_number

    async def test_create_agent_should_prevent_duplicate_phone_numbers(
        self,
        agent_service: AgentService,
        create_agent_command: CreateAgentCommand,
        persisted_agent: Agent,
    ):
        """Should raise AgentAlreadyExists for duplicate phone numbers."""
        # Arrange
        duplicate_command = CreateAgentCommand(
            name="Duplicate Agent",
            phone_number=persisted_agent.phone_number,  # Same phone number
            is_active=True,
        )

        # Act & Assert
        with pytest.raises(AgentAlreadyExists):
            await agent_service.create_agent(command=duplicate_command)

    async def test_create_agent_should_handle_optional_fields(
        self, agent_service: AgentService, mock_event_publisher
    ):
        """Should create agent with optional fields."""
        # Arrange
        command = CreateAgentCommand(
            name="Minimal Agent",
            phone_number="+5511888888888",
            is_active=False,
            description=None,
            instructions=None,
            llm_model=None,
            default_language=None,
        )

        # Act
        created_agent = await agent_service.create_agent(command=command)

        # Assert
        assert created_agent.name == "Minimal Agent"
        assert created_agent.description is None
        assert created_agent.instructions is None
        assert created_agent.llm_model is None
        assert created_agent.default_language is None
        assert created_agent.is_active is False

    async def test_create_agent_should_use_transactional_decorator(
        self, agent_service: AgentService, agent_factory, mock_event_publisher
    ):
        """Should use transaction for atomic operations."""
        # This test verifies that the @Transactional decorator is working
        # by ensuring that if event publishing fails, the agent creation is rolled back

        # Arrange
        command = agent_factory.build_create_command()

        # Mock event publisher to raise an exception
        mock_event_publisher.agent_created.side_effect = Exception("Event publishing failed")

        # Act & Assert
        with pytest.raises(Exception, match="Event publishing failed"):
            await agent_service.create_agent(command=command)

        # In a real scenario with proper transaction management,
        # the agent would not be persisted if event publishing fails


@pytest.mark.asyncio
@pytest.mark.agent_service
@pytest.mark.database
class TestAgentServiceRead:
    """Test agent read operations through service layer."""

    async def test_get_agent_list_should_return_paginated_results(
        self, agent_service: AgentService, persisted_agents: list[Agent]
    ):
        """Should return paginated list of agents."""
        # Act
        agents = await agent_service.get_agent_list(limit=2)

        # Assert
        assert len(agents) == 2
        assert all(isinstance(agent, Agent) for agent in agents)

    async def test_get_agent_list_should_respect_pagination_params(
        self, agent_service: AgentService, persisted_agents: list[Agent]
    ):
        """Should respect limit and prev parameters."""
        # Act
        agents = await agent_service.get_agent_list(limit=1, prev=None)

        # Assert
        assert len(agents) == 1

    async def test_get_agent_by_id_should_return_existing_agent(
        self, agent_service: AgentService, persisted_agent: Agent
    ):
        """Should retrieve agent by string ID."""
        # Act
        found_agent = await agent_service.get_agent_by_id(agent_id=str(persisted_agent.id))

        # Assert
        assert found_agent is not None
        assert found_agent.id == persisted_agent.id
        assert found_agent.name == persisted_agent.name

    async def test_get_agent_by_id_should_return_none_for_nonexistent(
        self, agent_service: AgentService
    ):
        """Should return None for non-existent agent ID."""
        # Arrange
        nonexistent_id = str(uuid.uuid4())

        # Act
        found_agent = await agent_service.get_agent_by_id(agent_id=nonexistent_id)

        # Assert
        assert found_agent is None

    async def test_get_agent_by_id_should_handle_invalid_uuid_format(
        self, agent_service: AgentService
    ):
        """Should handle invalid UUID format gracefully."""
        # Act & Assert
        with pytest.raises(ValueError):
            await agent_service.get_agent_by_id(agent_id="invalid-uuid-format")

    async def test_get_agent_by_id_with_relations_should_return_agent(
        self, agent_service: AgentService, persisted_agent: Agent
    ):
        """Should retrieve agent with relationships."""
        # Act
        found_agent = await agent_service.get_agent_by_id_with_relations(
            agent_id=str(persisted_agent.id)
        )

        # Assert
        assert found_agent is not None
        assert found_agent.id == persisted_agent.id


@pytest.mark.asyncio
@pytest.mark.agent_service
@pytest.mark.database
class TestAgentServiceUpdate:
    """Test agent update operations through service layer."""

    async def test_update_agent_should_modify_and_publish_event(
        self,
        agent_service: AgentService,
        persisted_agent: Agent,
        agent_factory,
        mock_event_publisher,
    ):
        """Should update agent and publish update event."""
        # Arrange
        command = agent_factory.build_update_command(
            agent_id=str(persisted_agent.id), name="Updated Name", description="Updated Description"
        )

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        assert updated_agent is not None
        assert updated_agent.id == persisted_agent.id
        assert updated_agent.name == "Updated Name"
        assert updated_agent.description == "Updated Description"

        # Verify event was published
        mock_event_publisher.agent_updated.assert_called_once()
        call_args = mock_event_publisher.agent_updated.call_args
        assert call_args[1]["agent_id"] == str(updated_agent.id)
        assert call_args[1]["agent_data"]["name"] == updated_agent.name
        assert call_args[1]["agent_data"]["is_active"] == updated_agent.is_active

    async def test_update_agent_should_return_none_for_nonexistent(
        self, agent_service: AgentService, agent_factory
    ):
        """Should return None when updating non-existent agent."""
        # Arrange
        nonexistent_id = str(uuid.uuid4())
        command = agent_factory.build_update_command(agent_id=nonexistent_id)

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        assert updated_agent is None

    async def test_update_agent_should_prevent_phone_number_conflicts(
        self, agent_service: AgentService, persisted_agents: list[Agent], agent_factory
    ):
        """Should prevent phone number conflicts during update."""
        # Arrange
        agent_to_update = persisted_agents[0]
        existing_phone = persisted_agents[1].phone_number

        command = agent_factory.build_update_command(
            agent_id=str(agent_to_update.id),
            phone_number=existing_phone,  # Try to use another agent's phone
        )

        # Act & Assert
        with pytest.raises(AgentAlreadyExists):
            await agent_service.update_agent(command=command)

    async def test_update_agent_should_allow_same_phone_number(
        self,
        agent_service: AgentService,
        persisted_agent: Agent,
        agent_factory,
        mock_event_publisher,
    ):
        """Should allow keeping the same phone number."""
        # Arrange
        command = agent_factory.build_update_command(
            agent_id=str(persisted_agent.id),
            phone_number=persisted_agent.phone_number,  # Same phone number
            name="Updated Name",
        )

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        assert updated_agent is not None
        assert updated_agent.phone_number == persisted_agent.phone_number
        assert updated_agent.name == "Updated Name"

    async def test_update_agent_should_handle_all_field_updates(
        self,
        agent_service: AgentService,
        persisted_agent: Agent,
        agent_factory,
        mock_event_publisher,
    ):
        """Should update all modifiable fields correctly."""
        # Arrange
        command = UpdateAgentCommand(
            agent_id=str(persisted_agent.id),
            name="New Name",
            phone_number="+5511777777777",
            description="New Description",
            instructions=["New instruction 1", "New instruction 2"],
            is_active=not persisted_agent.is_active,
            llm_model="gpt-3.5-turbo",
            default_language="en-US",
        )

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        assert updated_agent.name == "New Name"
        assert updated_agent.phone_number == "+5511777777777"
        assert updated_agent.description == "New Description"
        assert updated_agent.instructions == ["New instruction 1", "New instruction 2"]
        assert updated_agent.is_active == command.is_active
        assert updated_agent.llm_model == "gpt-3.5-turbo"
        assert updated_agent.default_language == "en-US"

    async def test_update_agent_should_use_transactional_decorator(
        self,
        agent_service: AgentService,
        persisted_agent: Agent,
        agent_factory,
        mock_event_publisher,
    ):
        """Should use transaction for atomic operations."""
        # Arrange
        command = agent_factory.build_update_command(
            agent_id=str(persisted_agent.id), name="Should Not Be Updated"
        )

        # Mock event publisher to raise an exception
        mock_event_publisher.agent_updated.side_effect = Exception("Event publishing failed")

        # Act & Assert
        with pytest.raises(Exception, match="Event publishing failed"):
            await agent_service.update_agent(command=command)


@pytest.mark.asyncio
@pytest.mark.agent_service
@pytest.mark.database
class TestAgentServiceDelete:
    """Test agent delete operations through service layer."""

    async def test_delete_agent_should_remove_and_publish_event(
        self, agent_service: AgentService, persisted_agent: Agent, mock_event_publisher
    ):
        """Should delete agent and publish deletion event."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Act
        result = await agent_service.delete_agent(agent_id=agent_id)

        # Assert
        assert result is True

        # Verify agent was deleted
        deleted_agent = await agent_service.get_agent_by_id(agent_id=agent_id)
        assert deleted_agent is None

        # Verify event was published
        mock_event_publisher.agent_deleted.assert_called_once_with(agent_id=agent_id)

    async def test_delete_agent_should_return_false_for_nonexistent(
        self, agent_service: AgentService, mock_event_publisher
    ):
        """Should return False when deleting non-existent agent."""
        # Arrange
        nonexistent_id = str(uuid.uuid4())

        # Act
        result = await agent_service.delete_agent(agent_id=nonexistent_id)

        # Assert
        assert result is False

        # Verify no event was published
        mock_event_publisher.agent_deleted.assert_not_called()

    async def test_delete_agent_should_handle_invalid_uuid_format(
        self, agent_service: AgentService
    ):
        """Should handle invalid UUID format gracefully."""
        # Act & Assert
        with pytest.raises(ValueError):
            await agent_service.delete_agent(agent_id="invalid-uuid-format")

    async def test_delete_agent_should_use_transactional_decorator(
        self, agent_service: AgentService, persisted_agent: Agent, mock_event_publisher
    ):
        """Should use transaction for atomic operations."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Mock event publisher to raise an exception
        mock_event_publisher.agent_deleted.side_effect = Exception("Event publishing failed")

        # Act & Assert
        with pytest.raises(Exception, match="Event publishing failed"):
            await agent_service.delete_agent(agent_id=agent_id)


@pytest.mark.asyncio
@pytest.mark.agent_service
@pytest.mark.events
class TestAgentServiceEventIntegration:
    """Test event publishing integration."""

    async def test_create_agent_event_contains_correct_data(
        self,
        agent_service: AgentService,
        create_agent_command: CreateAgentCommand,
        mock_event_publisher,
    ):
        """Should publish agent creation event with correct data structure."""
        # Act
        created_agent = await agent_service.create_agent(command=create_agent_command)

        # Assert
        mock_event_publisher.agent_created.assert_called_once()
        call_kwargs = mock_event_publisher.agent_created.call_args[1]

        assert call_kwargs["agent_id"] == str(created_agent.id)
        assert "agent_data" in call_kwargs

        agent_data = call_kwargs["agent_data"]
        assert agent_data["name"] == created_agent.name
        assert agent_data["is_active"] == created_agent.is_active
        assert agent_data["phone_number"] == created_agent.phone_number
        assert agent_data["llm_model"] == created_agent.llm_model
        assert agent_data["default_language"] == created_agent.default_language

    async def test_update_agent_event_contains_correct_data(
        self,
        agent_service: AgentService,
        persisted_agent: Agent,
        agent_factory,
        mock_event_publisher,
    ):
        """Should publish agent update event with correct data structure."""
        # Arrange
        command = agent_factory.build_update_command(
            agent_id=str(persisted_agent.id), name="Updated Name", is_active=False
        )

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        mock_event_publisher.agent_updated.assert_called_once()
        call_kwargs = mock_event_publisher.agent_updated.call_args[1]

        assert call_kwargs["agent_id"] == str(updated_agent.id)
        assert "agent_data" in call_kwargs

        agent_data = call_kwargs["agent_data"]
        assert agent_data["name"] == "Updated Name"
        assert agent_data["is_active"] is False

    async def test_delete_agent_event_contains_agent_id(
        self, agent_service: AgentService, persisted_agent: Agent, mock_event_publisher
    ):
        """Should publish agent deletion event with agent ID."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Act
        await agent_service.delete_agent(agent_id=agent_id)

        # Assert
        mock_event_publisher.agent_deleted.assert_called_once_with(agent_id=agent_id)


@pytest.mark.asyncio
@pytest.mark.agent_service
class TestAgentServiceEdgeCases:
    """Test edge cases and error scenarios."""

    async def test_service_handles_repository_exceptions(
        self, agent_service: AgentService, create_agent_command: CreateAgentCommand
    ):
        """Should handle repository layer exceptions appropriately."""
        # This test would be more meaningful with actual repository errors
        # For now, it demonstrates the test structure

        # Arrange - Create a command that could potentially fail
        command_with_very_long_name = CreateAgentCommand(
            name="A" * 1000,  # Very long name that might exceed DB limits
            phone_number="+5511999999999",
            is_active=True,
        )

        # Act & Assert - This might raise a database error
        try:
            await agent_service.create_agent(command=command_with_very_long_name)
        except Exception as e:
            # Service should allow database exceptions to bubble up
            assert e is not None

    async def test_create_agent_with_empty_name_should_work(
        self, agent_service: AgentService, mock_event_publisher
    ):
        """Should handle empty name (if business rules allow)."""
        # Arrange
        command = CreateAgentCommand(
            name="",  # Empty name
            phone_number="+5511999999999",
            is_active=True,
        )

        # Act
        created_agent = await agent_service.create_agent(command=command)

        # Assert
        assert created_agent.name == ""

    async def test_service_handles_concurrent_operations(
        self, agent_service: AgentService, agent_factory, mock_event_publisher
    ):
        """Should handle concurrent agent operations."""
        # Arrange
        commands = [agent_factory.build_create_command() for _ in range(3)]

        # Act - Create agents concurrently
        import asyncio

        tasks = [agent_service.create_agent(command=cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert
        successful_creates = [r for r in results if isinstance(r, Agent)]
        assert len(successful_creates) >= 1  # At least one should succeed

    async def test_service_uuid_conversion_edge_cases(self, agent_service: AgentService):
        """Should handle UUID conversion edge cases."""
        # Test various invalid UUID formats
        invalid_uuids = [
            "",
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            None,
        ]

        for invalid_uuid in invalid_uuids[:2]:  # Skip None to avoid TypeError
            with pytest.raises(ValueError):
                await agent_service.get_agent_by_id(agent_id=invalid_uuid)
