"""
Factory for creating task-specific HuggingFace pipelines.

Simple factory that creates properly configured pipelines for different
AI tasks. No over-engineering, just clean pipeline creation.
"""

from core.logger import get_module_logger

from .model_registry import ModelRegistry


logger = get_module_logger(__name__)


class PipelineFactory:
    """
    Factory for creating HuggingFace pipelines for specific AI tasks.

    Maps business tasks to appropriate HuggingFace pipeline configurations.
    Keeps pipeline creation logic centralized and easy to modify.
    """

    @staticmethod
    def get_task_config(business_task: str) -> dict[str, str]:
        """
        Get HuggingFace task configuration for business task.

        Args:
            business_task: Business task name (e.g., "fraud_detection")

        Returns:
            Dict with 'hf_task' and 'default_model' keys

        Raises:
            ValueError: If business task is not supported
        """
        task_configs = {
            "fraud_detection": {
                "hf_task": "text-classification",
                "default_model": ModelRegistry.get_model_for_task("fraud_detection", "default"),
            },
            "sentiment_analysis": {
                "hf_task": "sentiment-analysis",
                "default_model": ModelRegistry.get_model_for_task("sentiment_analysis", "default"),
            },
            "content_moderation": {
                "hf_task": "text-classification",
                "default_model": ModelRegistry.get_model_for_task("content_moderation", "default"),
            },
            "text_classification": {
                "hf_task": "zero-shot-classification",
                "default_model": ModelRegistry.get_model_for_task("text_classification", "default"),
            },
        }

        if business_task not in task_configs:
            available_tasks = list(task_configs.keys())
            msg = f"Unsupported business task: {business_task}. Available: {available_tasks}"
            raise ValueError(msg)

        return task_configs[business_task]

    @classmethod
    def create_pipeline_config(cls, business_task: str, model_variant: str = "default") -> dict:
        """
        Create pipeline configuration for a business task.

        Args:
            business_task: Business task name
            model_variant: Model variant to use

        Returns:
            Configuration dict for pipeline creation
        """
        task_config = cls.get_task_config(business_task)
        model_id = ModelRegistry.get_model_for_task(business_task, model_variant)

        return {
            "hf_task": task_config["hf_task"],
            "model_id": model_id,
            "business_task": business_task,
            "model_variant": model_variant,
        }

    @staticmethod
    def get_supported_tasks() -> list[str]:
        """Get list of supported business tasks."""
        return [
            "fraud_detection",
            "sentiment_analysis",
            "content_moderation",
            "text_classification",
        ]
