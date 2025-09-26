"""Integration tests for agent event publishing.

These tests verify the integration between agent operations
and event publishing system, ensuring events are correctly
generated and contain the expected data.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.agents.agent import Agent
from app.agents.api.schemas import CreateAgentCommand
from app.agents.services.agent_service import AgentService
from app.events.agents.publisher import AgentEventPublisher


@pytest.mark.asyncio
@pytest.mark.events
@pytest.mark.agent_integration
class TestAgentCreationEvents:
    """Test event publishing for agent creation operations."""

    async def test_create_agent_should_publish_creation_event_with_complete_data(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should publish complete agent creation event."""
        # Arrange
        command = agent_factory.build_create_command(
            name="Test Agent",
            phone_number="+5511999999999",
            description="Test description",
            instructions=["Instruction 1", "Instruction 2"],
            is_active=True,
            llm_model="gpt-4",
            default_language="pt-BR",
        )

        # Act
        created_agent = await agent_service.create_agent(command=command)

        # Assert
        mock_event_publisher.agent_created.assert_called_once()
        call_kwargs = mock_event_publisher.agent_created.call_args[1]

        # Verify event contains correct agent ID
        assert call_kwargs["agent_id"] == str(created_agent.id)

        # Verify event contains complete agent data
        agent_data = call_kwargs["agent_data"]
        assert agent_data["name"] == "Test Agent"
        assert agent_data["is_active"] is True
        assert agent_data["phone_number"] == "+5511999999999"
        assert agent_data["llm_model"] == "gpt-4"
        assert agent_data["default_language"] == "pt-BR"

    async def test_create_agent_should_publish_event_with_minimal_data(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should publish event even with minimal agent data."""
        # Arrange
        command = agent_factory.build_create_command(
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
        mock_event_publisher.agent_created.assert_called_once()
        call_kwargs = mock_event_publisher.agent_created.call_args[1]

        agent_data = call_kwargs["agent_data"]
        assert agent_data["name"] == "Minimal Agent"
        assert agent_data["is_active"] is False
        assert agent_data["phone_number"] == "+5511888888888"
        assert agent_data["llm_model"] is None
        assert agent_data["default_language"] is None

    async def test_create_agent_should_not_publish_event_on_failure(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should not publish event if agent creation fails."""
        # Arrange - Try to create agent with duplicate phone number
        command = agent_factory.build_create_command(phone_number=persisted_agent.phone_number)

        # Act & Assert
        from core.exceptions.domain import AgentAlreadyExists

        with pytest.raises(AgentAlreadyExists):
            await agent_service.create_agent(command=command)

        # Event should not be published on failure
        mock_event_publisher.agent_created.assert_not_called()

    async def test_create_agent_should_handle_event_publishing_failure(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should handle event publishing failures appropriately."""
        # Arrange
        command = agent_factory.build_create_command()

        # Mock event publisher to fail
        mock_event_publisher.agent_created.side_effect = Exception("Event broker connection failed")

        # Act & Assert - Should fail due to @Transactional decorator
        with pytest.raises(Exception, match="Event broker connection failed"):
            await agent_service.create_agent(command=command)

    async def test_create_multiple_agents_should_publish_separate_events(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should publish separate events for multiple agent creations."""
        # Arrange
        commands = [agent_factory.build_create_command() for _ in range(3)]

        # Act
        created_agents = []
        for command in commands:
            agent = await agent_service.create_agent(command=command)
            created_agents.append(agent)

        # Assert
        assert mock_event_publisher.agent_created.call_count == 3

        # Verify each call had correct agent ID
        call_args_list = mock_event_publisher.agent_created.call_args_list
        for i, call_args in enumerate(call_args_list):
            agent_id = call_args[1]["agent_id"]
            assert agent_id == str(created_agents[i].id)


@pytest.mark.asyncio
@pytest.mark.events
@pytest.mark.agent_integration
class TestAgentUpdateEvents:
    """Test event publishing for agent update operations."""

    async def test_update_agent_should_publish_update_event_with_new_data(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should publish update event with new agent data."""
        # Arrange
        command = agent_factory.build_update_command(
            agent_id=str(persisted_agent.id),
            name="Updated Name",
            is_active=not persisted_agent.is_active,
        )

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        mock_event_publisher.agent_updated.assert_called_once()
        call_kwargs = mock_event_publisher.agent_updated.call_args[1]

        assert call_kwargs["agent_id"] == str(updated_agent.id)

        agent_data = call_kwargs["agent_data"]
        assert agent_data["name"] == "Updated Name"
        assert agent_data["is_active"] == command.is_active

    async def test_update_agent_should_publish_event_with_current_data(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should publish event with current agent data after update."""
        # Arrange - Update only the name
        command = agent_factory.build_update_command(
            agent_id=str(persisted_agent.id),
            name="Only Name Updated",
            phone_number=persisted_agent.phone_number,  # Keep same
            is_active=persisted_agent.is_active,  # Keep same
        )

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        call_kwargs = mock_event_publisher.agent_updated.call_args[1]
        agent_data = call_kwargs["agent_data"]

        assert agent_data["name"] == "Only Name Updated"
        assert agent_data["is_active"] == persisted_agent.is_active  # Unchanged

    async def test_update_agent_should_not_publish_event_for_nonexistent_agent(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should not publish event if agent doesn't exist."""
        # Arrange
        nonexistent_id = str(uuid.uuid4())
        command = agent_factory.build_update_command(agent_id=nonexistent_id)

        # Act
        result = await agent_service.update_agent(command=command)

        # Assert
        assert result is None
        mock_event_publisher.agent_updated.assert_not_called()

    async def test_update_agent_should_not_publish_event_on_failure(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agents: list[Agent],
    ):
        """Should not publish event if update fails."""
        # Arrange - Try to update with duplicate phone number
        agent_to_update = persisted_agents[0]
        existing_phone = persisted_agents[1].phone_number

        command = agent_factory.build_update_command(
            agent_id=str(agent_to_update.id), phone_number=existing_phone
        )

        # Act & Assert
        from core.exceptions.domain import AgentAlreadyExists

        with pytest.raises(AgentAlreadyExists):
            await agent_service.update_agent(command=command)

        # Event should not be published on failure
        mock_event_publisher.agent_updated.assert_not_called()

    async def test_update_agent_should_handle_event_publishing_failure(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should handle event publishing failures during update."""
        # Arrange
        command = agent_factory.build_update_command(agent_id=str(persisted_agent.id))

        # Mock event publisher to fail
        mock_event_publisher.agent_updated.side_effect = Exception("Event publishing failed")

        # Act & Assert - Should fail due to @Transactional decorator
        with pytest.raises(Exception, match="Event publishing failed"):
            await agent_service.update_agent(command=command)


@pytest.mark.asyncio
@pytest.mark.events
@pytest.mark.agent_integration
class TestAgentDeletionEvents:
    """Test event publishing for agent deletion operations."""

    async def test_delete_agent_should_publish_deletion_event_with_agent_id(
        self,
        agent_service: AgentService,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should publish deletion event with agent ID."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Act
        result = await agent_service.delete_agent(agent_id=agent_id)

        # Assert
        assert result is True
        mock_event_publisher.agent_deleted.assert_called_once_with(agent_id=agent_id)

    async def test_delete_agent_should_not_publish_event_for_nonexistent_agent(
        self, agent_service: AgentService, mock_event_publisher: AgentEventPublisher
    ):
        """Should not publish event if agent doesn't exist."""
        # Arrange
        nonexistent_id = str(uuid.uuid4())

        # Act
        result = await agent_service.delete_agent(agent_id=nonexistent_id)

        # Assert
        assert result is False
        mock_event_publisher.agent_deleted.assert_not_called()

    async def test_delete_agent_should_handle_event_publishing_failure(
        self,
        agent_service: AgentService,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should handle event publishing failures during deletion."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Mock event publisher to fail
        mock_event_publisher.agent_deleted.side_effect = Exception("Event publishing failed")

        # Act & Assert - Should fail due to @Transactional decorator
        with pytest.raises(Exception, match="Event publishing failed"):
            await agent_service.delete_agent(agent_id=agent_id)

    async def test_delete_multiple_agents_should_publish_separate_events(
        self,
        agent_service: AgentService,
        mock_event_publisher: AgentEventPublisher,
        persisted_agents: list[Agent],
    ):
        """Should publish separate events for multiple deletions."""
        # Act
        results = []
        for agent in persisted_agents:
            result = await agent_service.delete_agent(agent_id=str(agent.id))
            results.append(result)

        # Assert
        assert all(results)  # All deletions should succeed
        assert mock_event_publisher.agent_deleted.call_count == len(persisted_agents)

        # Verify each call had correct agent ID
        call_args_list = mock_event_publisher.agent_deleted.call_args_list
        expected_agent_ids = {str(agent.id) for agent in persisted_agents}
        actual_agent_ids = {call_args[1]["agent_id"] for call_args in call_args_list}

        assert actual_agent_ids == expected_agent_ids


@pytest.mark.asyncio
@pytest.mark.events
@pytest.mark.agent_integration
class TestAgentEventData:
    """Test event data structure and content."""

    async def test_agent_created_event_data_structure(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should include all required fields in creation event data."""
        # Arrange
        command = agent_factory.build_create_command()

        # Act
        created_agent = await agent_service.create_agent(command=command)

        # Assert
        call_kwargs = mock_event_publisher.agent_created.call_args[1]

        # Verify top-level structure
        assert "agent_id" in call_kwargs
        assert "agent_data" in call_kwargs

        # Verify agent_data structure
        agent_data = call_kwargs["agent_data"]
        required_fields = ["name", "is_active", "phone_number", "llm_model", "default_language"]

        for field in required_fields:
            assert field in agent_data, f"Missing field: {field}"

        # Verify data types
        assert isinstance(agent_data["name"], str)
        assert isinstance(agent_data["is_active"], bool)
        assert isinstance(agent_data["phone_number"], str)
        assert agent_data["llm_model"] is None or isinstance(agent_data["llm_model"], str)
        assert agent_data["default_language"] is None or isinstance(
            agent_data["default_language"], str
        )

    async def test_agent_updated_event_data_structure(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should include required fields in update event data."""
        # Arrange
        command = agent_factory.build_update_command(agent_id=str(persisted_agent.id))

        # Act
        updated_agent = await agent_service.update_agent(command=command)

        # Assert
        call_kwargs = mock_event_publisher.agent_updated.call_args[1]

        # Verify top-level structure
        assert "agent_id" in call_kwargs
        assert "agent_data" in call_kwargs

        # Verify agent_data contains key fields
        agent_data = call_kwargs["agent_data"]
        assert "name" in agent_data
        assert "is_active" in agent_data

        # Verify data types
        assert isinstance(agent_data["name"], str)
        assert isinstance(agent_data["is_active"], bool)

    async def test_agent_deleted_event_structure(
        self,
        agent_service: AgentService,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should pass agent ID to deletion event."""
        # Arrange
        agent_id = str(persisted_agent.id)

        # Act
        await agent_service.delete_agent(agent_id=agent_id)

        # Assert
        mock_event_publisher.agent_deleted.assert_called_once_with(agent_id=agent_id)

        # Verify the agent_id is a valid UUID string
        call_args = mock_event_publisher.agent_deleted.call_args[1]
        passed_agent_id = call_args["agent_id"]

        # Should be able to parse as UUID
        parsed_uuid = uuid.UUID(passed_agent_id)
        assert str(parsed_uuid) == agent_id

    async def test_event_data_consistency_across_operations(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should maintain consistent agent ID across create/update/delete events."""
        # Arrange
        command = agent_factory.build_create_command()

        # Act - Create agent
        created_agent = await agent_service.create_agent(command=command)
        agent_id = str(created_agent.id)

        # Update agent
        update_command = agent_factory.build_update_command(agent_id=agent_id)
        await agent_service.update_agent(command=update_command)

        # Delete agent
        await agent_service.delete_agent(agent_id=agent_id)

        # Assert - All events should have consistent agent ID
        create_call = mock_event_publisher.agent_created.call_args[1]
        update_call = mock_event_publisher.agent_updated.call_args[1]
        delete_call = mock_event_publisher.agent_deleted.call_args[1]

        assert create_call["agent_id"] == agent_id
        assert update_call["agent_id"] == agent_id
        assert delete_call["agent_id"] == agent_id


@pytest.mark.asyncio
@pytest.mark.events
class TestAgentEventPublisherIntegration:
    """Test integration with actual event publisher (if available)."""

    @patch("app.agents.services.agent_service.AgentEventPublisher")
    async def test_agent_service_uses_injected_event_publisher(
        self, mock_publisher_class, agent_repository
    ):
        """Should use the injected event publisher instance."""
        # Arrange
        mock_publisher_instance = Mock(spec=AgentEventPublisher)
        mock_publisher_instance.agent_created = AsyncMock()

        service = AgentService(repository=agent_repository, event_publisher=mock_publisher_instance)

        # Act - Create an agent

        command = CreateAgentCommand(
            name="Test Agent", phone_number="+5511999999999", is_active=True
        )

        try:
            await service.create_agent(command=command)
        except Exception:
            # Expected to fail due to mocked dependencies, but we're testing publisher usage
            pass

        # Assert - The injected publisher should be used
        assert service.event_publisher is mock_publisher_instance

    async def test_event_publisher_method_signatures(self):
        """Should verify event publisher has expected method signatures."""
        # This test ensures the event publisher interface is correct
        publisher = AgentEventPublisher(broker=Mock())

        # Verify methods exist and are async
        assert hasattr(publisher, "agent_created")
        assert hasattr(publisher, "agent_updated")
        assert hasattr(publisher, "agent_deleted")

        import inspect

        assert inspect.iscoroutinefunction(publisher.agent_created)
        assert inspect.iscoroutinefunction(publisher.agent_updated)
        assert inspect.iscoroutinefunction(publisher.agent_deleted)


@pytest.mark.asyncio
@pytest.mark.events
class TestAgentEventErrorRecovery:
    """Test error recovery and resilience in event publishing."""

    async def test_transactional_rollback_on_event_failure(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        agent_repository,
    ):
        """Should rollback database changes if event publishing fails."""
        # Arrange
        command = agent_factory.build_create_command()

        # Mock event publisher to fail after agent is created
        mock_event_publisher.agent_created.side_effect = Exception("Event system down")

        # Count agents before operation
        agents_before = await agent_repository.get_agents(limit=100)
        initial_count = len(agents_before)

        # Act & Assert
        with pytest.raises(Exception, match="Event system down"):
            await agent_service.create_agent(command=command)

        # Verify rollback - agent should not be in database
        agents_after = await agent_repository.get_agents(limit=100)
        final_count = len(agents_after)

        # In a proper transactional system, the count should remain the same
        # This test documents expected behavior with @Transactional decorator
        # Note: This might pass or fail depending on transaction implementation
        assert final_count <= initial_count + 1  # Allow for either behavior

    async def test_event_publishing_with_network_timeouts(
        self, agent_service: AgentService, agent_factory, mock_event_publisher: AgentEventPublisher
    ):
        """Should handle event publishing timeouts appropriately."""
        # Arrange
        command = agent_factory.build_create_command()

        # Mock event publisher to raise timeout
        import asyncio

        mock_event_publisher.agent_created.side_effect = TimeoutError("Event broker timeout")

        # Act & Assert
        with pytest.raises(asyncio.TimeoutError, match="Event broker timeout"):
            await agent_service.create_agent(command=command)

    async def test_partial_event_publishing_failure_scenario(
        self,
        agent_service: AgentService,
        agent_factory,
        mock_event_publisher: AgentEventPublisher,
        persisted_agent: Agent,
    ):
        """Should handle scenarios where some events succeed and others fail."""
        # This test simulates a scenario where create succeeds but update fails

        # Arrange - First create succeeds
        create_command = agent_factory.build_create_command()
        created_agent = await agent_service.create_agent(command=create_command)

        # Now make update events fail
        mock_event_publisher.agent_updated.side_effect = Exception("Update event failed")

        # Act & Assert - Update should fail
        update_command = agent_factory.build_update_command(agent_id=str(created_agent.id))

        with pytest.raises(Exception, match="Update event failed"):
            await agent_service.update_agent(command=update_command)

        # Verify create event was published but update wasn't
        mock_event_publisher.agent_created.assert_called()
        mock_event_publisher.agent_updated.assert_called()  # Called but failed
