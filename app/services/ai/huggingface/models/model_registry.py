"""
Registry of models for different AI tasks.

Simple mapping of AI tasks to recommended models. No over-engineering,
just clear model selections for specific business use cases.
"""


class ModelRegistry:
    """
    Registry of HuggingFace models for specific AI tasks.

    Organized by business use case, not generic tasks.
    Makes it easy to upgrade models or add alternatives.
    """

    # Fraud Detection Models
    FRAUD_DETECTION = {
        "default": "distilbert-base-uncased",  # Fast and reliable for classification
        "advanced": "microsoft/DialoGPT-medium",  # More sophisticated analysis
    }

    # Sentiment Analysis Models
    SENTIMENT_ANALYSIS = {
        "default": "cardiffnlp/twitter-roberta-base-sentiment-latest",  # General sentiment
        "customer_feedback": "nlptown/bert-base-multilingual-uncased-sentiment",  # Customer-focused
        "financial": "ProsusAI/finbert",  # Financial sentiment analysis
    }

    # Content Moderation Models
    CONTENT_MODERATION = {
        "default": "unitary/toxic-bert",  # General toxicity detection
        "comprehensive": "martin-ha/toxic-comment-model",  # Multi-category toxicity
        "hate_speech": "cardiffnlp/twitter-roberta-base-hate-latest",  # Hate speech detection
    }

    # Text Classification Models
    TEXT_CLASSIFICATION = {
        "default": "facebook/bart-large-mnli",  # Zero-shot classification
        "lightweight": "distilbert-base-uncased",  # Fast classification
        "multilingual": "microsoft/mdeberta-v3-base",  # Multi-language support
    }

    @classmethod
    def get_model_for_task(cls, task: str, variant: str = "default") -> str:
        """
        Get model ID for a specific task and variant.

        Args:
            task: Task name (e.g., "fraud_detection", "sentiment_analysis")
            variant: Model variant (e.g., "default", "advanced", "lightweight")

        Returns:
            HuggingFace model identifier

        Raises:
            ValueError: If task or variant is not found
        """
        task_mapping = {
            "fraud_detection": cls.FRAUD_DETECTION,
            "sentiment_analysis": cls.SENTIMENT_ANALYSIS,
            "content_moderation": cls.CONTENT_MODERATION,
            "text_classification": cls.TEXT_CLASSIFICATION,
        }

        if task not in task_mapping:
            available_tasks = list(task_mapping.keys())
            raise ValueError(f"Unknown task: {task}. Available: {available_tasks}")

        task_models = task_mapping[task]
        if variant not in task_models:
            available_variants = list(task_models.keys())
            msg = f"Unknown variant '{variant}' for task '{task}'. Available: {available_variants}"
            raise ValueError(msg)

        return task_models[variant]

    @classmethod
    def get_available_tasks(cls) -> list[str]:
        """Get list of available AI tasks."""
        return [
            "fraud_detection",
            "sentiment_analysis",
            "content_moderation",
            "text_classification",
        ]

    @classmethod
    def get_available_variants(cls, task: str) -> list[str]:
        """Get available model variants for a specific task."""
        task_mapping = {
            "fraud_detection": cls.FRAUD_DETECTION,
            "sentiment_analysis": cls.SENTIMENT_ANALYSIS,
            "content_moderation": cls.CONTENT_MODERATION,
            "text_classification": cls.TEXT_CLASSIFICATION,
        }

        if task not in task_mapping:
            raise ValueError(f"Unknown task: {task}")

        return list(task_mapping[task].keys())
