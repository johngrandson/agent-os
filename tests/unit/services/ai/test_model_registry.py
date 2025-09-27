"""
Tests for Model Registry.

Tests model configuration and task mapping functionality.
"""

import pytest
from app.services.ai.huggingface.models.model_registry import ModelRegistry


class TestModelRegistry:
    """Test model registry functionality."""

    def test_get_model_for_task_default(self):
        """Test getting default model for a task."""
        model_id = ModelRegistry.get_model_for_task("fraud_detection", "default")
        assert model_id == "distilbert-base-uncased"

    def test_get_model_for_task_advanced(self):
        """Test getting advanced model variant."""
        model_id = ModelRegistry.get_model_for_task("fraud_detection", "advanced")
        assert model_id == "microsoft/DialoGPT-medium"

    def test_get_model_for_task_sentiment_default(self):
        """Test getting default sentiment analysis model."""
        model_id = ModelRegistry.get_model_for_task("sentiment_analysis", "default")
        assert model_id == "cardiffnlp/twitter-roberta-base-sentiment-latest"

    def test_get_model_for_task_content_moderation(self):
        """Test getting content moderation model."""
        model_id = ModelRegistry.get_model_for_task("content_moderation", "default")
        assert model_id == "unitary/toxic-bert"

    def test_get_model_for_task_unknown_task(self):
        """Test error handling for unknown task."""
        with pytest.raises(ValueError) as exc_info:
            ModelRegistry.get_model_for_task("unknown_task", "default")

        assert "Unknown task: unknown_task" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_get_model_for_task_unknown_variant(self):
        """Test error handling for unknown variant."""
        with pytest.raises(ValueError) as exc_info:
            ModelRegistry.get_model_for_task("fraud_detection", "unknown_variant")

        assert "Unknown variant 'unknown_variant'" in str(exc_info.value)
        assert "fraud_detection" in str(exc_info.value)

    def test_get_available_tasks(self):
        """Test getting list of available tasks."""
        tasks = ModelRegistry.get_available_tasks()

        expected_tasks = [
            "fraud_detection",
            "sentiment_analysis",
            "content_moderation",
            "text_classification",
        ]

        assert set(tasks) == set(expected_tasks)

    def test_get_available_variants_fraud_detection(self):
        """Test getting variants for fraud detection."""
        variants = ModelRegistry.get_available_variants("fraud_detection")

        expected_variants = ["default", "advanced"]
        assert set(variants) == set(expected_variants)

    def test_get_available_variants_sentiment_analysis(self):
        """Test getting variants for sentiment analysis."""
        variants = ModelRegistry.get_available_variants("sentiment_analysis")

        expected_variants = ["default", "customer_feedback", "financial"]
        assert set(variants) == set(expected_variants)

    def test_get_available_variants_unknown_task(self):
        """Test error handling for unknown task in variants."""
        with pytest.raises(ValueError) as exc_info:
            ModelRegistry.get_available_variants("unknown_task")

        assert "Unknown task: unknown_task" in str(exc_info.value)

    def test_all_model_registries_have_default(self):
        """Test that all model registries have a default variant."""
        assert "default" in ModelRegistry.FRAUD_DETECTION
        assert "default" in ModelRegistry.SENTIMENT_ANALYSIS
        assert "default" in ModelRegistry.CONTENT_MODERATION
        assert "default" in ModelRegistry.TEXT_CLASSIFICATION

    def test_model_ids_are_strings(self):
        """Test that all model IDs are valid strings."""
        for task in ModelRegistry.get_available_tasks():
            variants = ModelRegistry.get_available_variants(task)
            for variant in variants:
                model_id = ModelRegistry.get_model_for_task(task, variant)
                assert isinstance(model_id, str)
                assert len(model_id) > 0
                assert "/" in model_id or "-" in model_id  # Valid HuggingFace format
