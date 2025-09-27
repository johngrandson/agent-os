"""Model factory for creating Agno-compatible AI models"""

from agno.models.openai import OpenAIChat
from core.config import Config
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class AgnoModelFactory:
    """Factory for creating AI models compatible with Agno"""

    def __init__(self, config: Config):
        self.config = config
        logger.info("AgnoModelFactory initialized")

    def create_default_model(self) -> OpenAIChat:
        """
        Create the default AI model for agents.

        Returns:
            Configured OpenAIChat model
        """
        model_name = self.config.AGNO_DEFAULT_MODEL
        logger.info(f"Creating default model: {model_name}")

        return OpenAIChat(id=model_name)

    def create_openai_model(self, model_id: str) -> OpenAIChat:
        """
        Create an OpenAI model with specific ID.

        Args:
            model_id: OpenAI model identifier

        Returns:
            Configured OpenAIChat model
        """
        logger.info(f"Creating OpenAI model: {model_id}")
        return OpenAIChat(id=model_id)

    def create_model_for_context(self, context: str) -> OpenAIChat:
        """
        Create an appropriate model based on context.

        Args:
            context: Usage context (e.g., 'webhook', 'agent_os', 'chat')

        Returns:
            Configured model appropriate for the context
        """
        # For now, return default model
        # In the future, this could select different models based on context
        logger.info(f"Creating model for context: {context}")
        return self.create_default_model()
