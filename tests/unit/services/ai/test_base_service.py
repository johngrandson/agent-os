"""
Tests for base HuggingFace service functionality.

Tests the core service foundation without requiring actual model downloads.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.services.ai.huggingface.huggingface_service import HuggingFaceService


class TestHuggingFaceService:
    """Test the base HuggingFace service functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a concrete implementation of the abstract base service for testing."""

        class ConcreteHuggingFaceService(HuggingFaceService):
            """Concrete implementation for testing."""

            pass

        return ConcreteHuggingFaceService()

    def test_service_initialization(self, mock_service):
        """Test that service initializes correctly."""
        assert mock_service.config is not None
        assert mock_service._pipelines == {}
        assert mock_service._executor is not None

    @patch("app.services.ai.huggingface.huggingface_service.asyncio.get_event_loop")
    @patch.object(HuggingFaceService, "_create_pipeline")
    async def test_get_pipeline_caching(self, mock_create_pipeline, mock_get_loop, mock_service):
        """Test that pipelines are cached properly."""
        # Setup mocks
        mock_pipeline = Mock()
        mock_create_pipeline.return_value = mock_pipeline

        mock_loop = Mock()
        mock_loop.run_in_executor = AsyncMock(return_value=mock_pipeline)
        mock_get_loop.return_value = mock_loop

        # First call should create pipeline
        result1 = await mock_service.get_pipeline("sentiment-analysis", "test-model")
        assert result1 == mock_pipeline
        assert mock_loop.run_in_executor.called

        # Reset mock to verify caching
        mock_loop.run_in_executor.reset_mock()

        # Second call should use cached pipeline
        result2 = await mock_service.get_pipeline("sentiment-analysis", "test-model")
        assert result2 == mock_pipeline
        assert not mock_loop.run_in_executor.called  # Should not call executor again

    @patch("app.services.ai.huggingface.huggingface_service.pipeline")
    def test_create_pipeline_success(self, mock_pipeline_func, mock_service):
        """Test successful pipeline creation."""
        mock_pipeline = Mock()
        mock_pipeline_func.return_value = mock_pipeline

        result = mock_service._create_pipeline("sentiment-analysis", "test-model")

        assert result == mock_pipeline
        mock_pipeline_func.assert_called_once_with(
            task="sentiment-analysis",
            model="test-model",
            tokenizer="test-model",
            token=None,  # Default when no token configured
            return_all_scores=False,
        )

    @patch("app.services.ai.huggingface.huggingface_service.pipeline")
    def test_create_pipeline_with_token(self, mock_pipeline_func, mock_service):
        """Test pipeline creation with API token."""
        mock_service.config.HUGGINGFACE_API_TOKEN = "test-token"
        mock_pipeline = Mock()
        mock_pipeline_func.return_value = mock_pipeline

        result = mock_service._create_pipeline("text-classification", "test-model")

        assert result == mock_pipeline
        mock_pipeline_func.assert_called_once_with(
            task="text-classification",
            model="test-model",
            tokenizer="test-model",
            token="test-token",
            return_all_scores=True,  # True for text-classification
        )

    @patch("app.services.ai.huggingface.huggingface_service.pipeline")
    def test_create_pipeline_error(self, mock_pipeline_func, mock_service):
        """Test pipeline creation error handling."""
        mock_pipeline_func.side_effect = Exception("Model not found")

        with pytest.raises(Exception) as exc_info:
            mock_service._create_pipeline("sentiment-analysis", "invalid-model")

        assert "Model not found" in str(exc_info.value)

    @patch("app.services.ai.huggingface.huggingface_service.asyncio.get_event_loop")
    async def test_run_pipeline(self, mock_get_loop, mock_service):
        """Test pipeline execution in thread pool."""
        mock_pipeline = Mock()
        mock_pipeline.return_value = ["test result"]

        mock_loop = Mock()
        mock_loop.run_in_executor = AsyncMock(return_value=["test result"])
        mock_get_loop.return_value = mock_loop

        result = await mock_service._run_pipeline(mock_pipeline, "test text")

        assert result == ["test result"]
        mock_loop.run_in_executor.assert_called_once_with(
            mock_service._executor, mock_pipeline, "test text"
        )
