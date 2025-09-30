"""
Tests for AccuracyEvalService

Tests the evaluation feedback system to ensure:
- Evaluations run correctly with configured agents
- eval_id extraction from AccuracyEval object
- avg_score extraction from result.compute_stats()
- Event publishing for failed evaluations
- NO event publishing for passing evaluations
- NO event publishing when eval_id is "unknown"
"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.domains.evaluation.services.accuracy_eval_service import AccuracyEvalService


class TestAccuracyEvalService:
    """Test the AccuracyEvalService functionality"""

    @pytest.fixture
    def mock_agent_provider(self) -> Mock:
        """Create mock AgnoProvider"""
        provider = Mock()
        mock_agent = Mock()
        mock_agent.name = "test-agent"
        provider.get_agent = AsyncMock(return_value=mock_agent)
        return provider

    @pytest.fixture
    def mock_event_publisher(self) -> Mock:
        """Create mock EvaluationEventPublisher"""
        publisher = Mock()
        publisher.eval_failed = AsyncMock()
        return publisher

    @pytest.fixture
    def service(self, mock_agent_provider: Mock, mock_event_publisher: Mock) -> AccuracyEvalService:
        """Create AccuracyEvalService with mocked dependencies"""
        with (
            patch("app.domains.evaluation.services.accuracy_eval_service.AgnoDatabaseFactory"),
            patch("app.domains.evaluation.services.accuracy_eval_service.broker"),
        ):
            service = AccuracyEvalService(agent_provider=mock_agent_provider)
            service.event_publisher = mock_event_publisher
            return service

    @pytest.mark.asyncio
    async def test_should_extract_eval_id_from_accuracy_eval_when_evaluation_runs(
        self, service: AccuracyEvalService, mock_agent_provider: Mock
    ):
        """Test that eval_id is correctly extracted from AccuracyEval.eval_id"""
        # Arrange
        expected_eval_id = "eval-12345"
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": 9.0})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = expected_eval_id
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="test-eval",
                input_text="test input",
                expected_output="test output",
                num_iterations=1,
            )

            # Assert
            assert result["eval_id"] == expected_eval_id
            assert mock_eval_instance.run.called

    @pytest.mark.asyncio
    async def test_should_extract_avg_score_from_result_compute_stats_when_evaluation_completes(
        self, service: AccuracyEvalService
    ):
        """Test that avg_score is correctly extracted from result.compute_stats()"""
        # Arrange
        expected_avg_score = 7.5
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": expected_avg_score})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-123"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="test-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            assert result["avg_score"] == expected_avg_score
            mock_result.compute_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_publish_event_when_evaluation_fails_with_score_below_8(
        self, service: AccuracyEvalService, mock_event_publisher: Mock
    ):
        """Test that evaluation.failed event is published when avg_score < 8.0"""
        # Arrange
        failing_score = 7.9
        eval_id = "eval-fail-123"
        agent_id = "agent-123"
        eval_name = "failing-eval"

        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": failing_score})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = eval_id
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id=agent_id,
                eval_name=eval_name,
                input_text="test input",
                expected_output="test output",
                num_iterations=2,
            )

            # Assert
            assert result["status"] == "failed"
            mock_event_publisher.eval_failed.assert_called_once()

            # Verify event data structure
            call_args = mock_event_publisher.eval_failed.call_args
            assert call_args.kwargs["agent_id"] == agent_id
            assert call_args.kwargs["eval_data"]["eval_id"] == eval_id
            assert call_args.kwargs["eval_data"]["eval_name"] == eval_name
            assert call_args.kwargs["eval_data"]["avg_score"] == failing_score
            assert call_args.kwargs["eval_data"]["input"] == "test input"
            assert call_args.kwargs["eval_data"]["expected_output"] == "test output"
            assert call_args.kwargs["eval_data"]["num_iterations"] == 2

    @pytest.mark.asyncio
    async def test_should_not_publish_event_when_evaluation_passes_with_score_8_or_above(
        self, service: AccuracyEvalService, mock_event_publisher: Mock
    ):
        """Test that NO event is published when avg_score >= 8.0"""
        # Arrange
        passing_score = 8.0
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": passing_score})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-pass-123"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="passing-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            assert result["status"] == "passed"
            mock_event_publisher.eval_failed.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_not_publish_event_when_eval_id_is_unknown(
        self, service: AccuracyEvalService, mock_event_publisher: Mock
    ):
        """Test that NO event is published when eval_id is 'unknown'"""
        # Arrange
        failing_score = 5.0
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": failing_score})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            # Simulate missing eval_id attribute
            delattr(mock_eval_instance, "eval_id") if hasattr(
                mock_eval_instance, "eval_id"
            ) else None
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="unknown-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            assert result["status"] == "failed"
            assert result["eval_id"] == "unknown"
            mock_event_publisher.eval_failed.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_handle_missing_compute_stats_method_gracefully(
        self, service: AccuracyEvalService
    ):
        """Test fallback when result doesn't have compute_stats method"""
        # Arrange
        mock_result = Mock()
        mock_result.avg_score = 6.5
        # Remove compute_stats method
        del mock_result.compute_stats

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-fallback"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="fallback-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            assert result["avg_score"] == 6.5
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_should_handle_none_result_gracefully(self, service: AccuracyEvalService):
        """Test fallback when result is None"""
        # Arrange
        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-none"
            mock_eval_instance.run = Mock(return_value=None)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="none-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            assert result["avg_score"] == 0.0
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_should_handle_empty_compute_stats_result(self, service: AccuracyEvalService):
        """Test fallback when compute_stats returns None or empty dict"""
        # Arrange
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value=None)

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-empty-stats"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="empty-stats-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            assert result["avg_score"] == 0.0
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_should_raise_error_when_agent_not_found(
        self, service: AccuracyEvalService, mock_agent_provider: Mock
    ):
        """Test that ValueError is raised when agent is not found"""
        # Arrange
        mock_agent_provider.get_agent = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.run_accuracy_eval(
                agent_id="nonexistent-agent",
                eval_name="test-eval",
                input_text="test input",
                expected_output="test output",
            )

        assert "Agent nonexistent-agent not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_should_pass_additional_guidelines_to_accuracy_eval(
        self, service: AccuracyEvalService
    ):
        """Test that additional_guidelines parameter is passed to AccuracyEval"""
        # Arrange
        additional_guidelines = "Be extra strict about grammar"
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": 9.0})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-guidelines"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="guidelines-eval",
                input_text="test input",
                expected_output="test output",
                additional_guidelines=additional_guidelines,
            )

            # Assert
            mock_accuracy_eval_class.assert_called_once()
            call_kwargs = mock_accuracy_eval_class.call_args.kwargs
            assert call_kwargs["additional_guidelines"] == additional_guidelines

    @pytest.mark.asyncio
    async def test_should_use_same_database_as_agent_os(self, service: AccuracyEvalService):
        """Test that AccuracyEval uses the same database as AgentOS"""
        # Arrange
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": 9.0})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-db"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="db-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            mock_accuracy_eval_class.assert_called_once()
            call_kwargs = mock_accuracy_eval_class.call_args.kwargs
            assert call_kwargs["db"] == service.db

    @pytest.mark.asyncio
    async def test_should_run_eval_in_thread_pool(self, service: AccuracyEvalService):
        """Test that eval.run() is executed in thread pool (via run_in_executor)"""
        # Arrange
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": 9.0})

        with (
            patch(
                "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
            ) as mock_accuracy_eval_class,
            patch("asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-thread"
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            mock_loop = Mock()
            mock_loop.run_in_executor = AsyncMock(return_value=mock_result)
            mock_get_loop.return_value = mock_loop

            # Act
            await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="thread-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            mock_loop.run_in_executor.assert_called_once()
            # Verify the callable passed to executor
            call_args = mock_loop.run_in_executor.call_args
            assert call_args[0][0] is None  # First arg should be None (default executor)

    @pytest.mark.asyncio
    async def test_should_pass_print_flags_to_eval_run(self, service: AccuracyEvalService):
        """Test that print_results=False and print_summary=False are passed to eval.run()"""
        # Arrange
        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": 9.0})
        run_mock = Mock(return_value=mock_result)

        with (
            patch(
                "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
            ) as mock_accuracy_eval_class,
            patch("asyncio.get_event_loop") as mock_get_loop,
        ):
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = "eval-print"
            mock_eval_instance.run = run_mock
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Mock the executor to actually call the function
            mock_loop = Mock()

            async def mock_executor(executor: Any, func: Any) -> Any:
                return func()

            mock_loop.run_in_executor = mock_executor
            mock_get_loop.return_value = mock_loop

            # Act
            await service.run_accuracy_eval(
                agent_id="agent-123",
                eval_name="print-eval",
                input_text="test input",
                expected_output="test output",
            )

            # Assert
            run_mock.assert_called_once_with(print_results=False, print_summary=False)

    @pytest.mark.asyncio
    async def test_should_return_complete_result_dictionary(self, service: AccuracyEvalService):
        """Test that the service returns a complete result dictionary with all expected fields"""
        # Arrange
        eval_id = "eval-complete"
        agent_id = "agent-123"
        eval_name = "complete-eval"
        avg_score = 8.5
        num_iterations = 3

        mock_result = Mock()
        mock_result.compute_stats = Mock(return_value={"avg_score": avg_score})

        with patch(
            "app.domains.evaluation.services.accuracy_eval_service.AccuracyEval"
        ) as mock_accuracy_eval_class:
            mock_eval_instance = Mock()
            mock_eval_instance.eval_id = eval_id
            mock_eval_instance.run = Mock(return_value=mock_result)
            mock_accuracy_eval_class.return_value = mock_eval_instance

            # Act
            result = await service.run_accuracy_eval(
                agent_id=agent_id,
                eval_name=eval_name,
                input_text="test input",
                expected_output="test output",
                num_iterations=num_iterations,
            )

            # Assert
            assert result["eval_id"] == eval_id
            assert result["agent_id"] == agent_id
            assert result["name"] == eval_name
            assert result["avg_score"] == avg_score
            assert result["num_iterations"] == num_iterations
            assert result["status"] == "passed"
            assert "message" in result
            assert str(avg_score) in result["message"]
