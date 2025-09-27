"""
Base HuggingFace service class providing common functionality.

Simple, focused base class for HuggingFace AI services. No over-engineering,
no complex abstractions - just the essentials.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from core.config import get_config
from core.logger import get_module_logger
from transformers import pipeline


logger = get_module_logger(__name__)


class HuggingFaceService:
    """
    Base class for HuggingFace AI services.

    Provides common functionality for pipeline management and async operations.
    Each specialized service inherits from this to implement specific AI tasks.
    """

    def __init__(self):
        self.config = get_config()
        self._pipelines: dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hf-service")
        logger.info(f"{self.__class__.__name__} initialized")

    async def get_pipeline(self, task: str, model_id: str) -> Any:
        """
        Get or create a HuggingFace pipeline for the specified task and model.

        Caches pipelines to avoid repeated loading. Runs sync operations
        in thread pool to maintain async compatibility.

        Args:
            task: HuggingFace task type (e.g., "sentiment-analysis", "text-classification")
            model_id: Model identifier from HuggingFace Hub

        Returns:
            HuggingFace pipeline ready for inference
        """
        cache_key = f"{task}:{model_id}"

        if cache_key not in self._pipelines:
            logger.info(f"Loading HuggingFace pipeline: {task} with model {model_id}")

            # Load pipeline in thread pool to avoid blocking
            pipeline = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._create_pipeline, task, model_id
            )

            self._pipelines[cache_key] = pipeline
            logger.info(f"Pipeline loaded successfully: {cache_key}")

        return self._pipelines[cache_key]

    def _create_pipeline(self, task: str, model_id: str) -> Any:
        """Create HuggingFace pipeline synchronously (runs in thread pool)."""
        try:
            return pipeline(
                task=task,
                model=model_id,
                tokenizer=model_id,
                token=self.config.HUGGINGFACE_API_TOKEN or None,
                return_all_scores=True if task == "text-classification" else False,
            )
        except Exception as e:
            logger.error(f"Failed to create pipeline for {task}:{model_id}: {e}")
            raise

    async def _run_pipeline(self, pipeline: Any, text: str) -> Any:
        """Run pipeline inference in thread pool to maintain async compatibility."""
        return await asyncio.get_event_loop().run_in_executor(self._executor, pipeline, text)

    def __del__(self):
        """Cleanup thread pool on service destruction."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
