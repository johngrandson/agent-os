"""
Simple provider factory for environment-based provider selection.
Following CLAUDE.md: boring over clever, single responsibility.
"""

import os

from app.providers.base import AgentProvider
from core.logger import get_module_logger


logger = get_module_logger(__name__)


def get_provider() -> AgentProvider:
    """
    Get the configured agent provider based on environment.

    Returns:
        Configured AgentProvider instance

    Raises:
        ValueError: If unknown provider is specified
    """
    provider_name = os.getenv("AGENT_PROVIDER", "agno")

    logger.info(f"Creating agent provider: {provider_name}")

    if provider_name == "agno":
        from app.providers.agno import AgnoProvider

        return AgnoProvider()

    # Future providers can be added here:
    # elif provider_name == "crewai":
    #     from app.providers.crewai_provider import CrewAIProvider
    #     return CrewAIProvider()

    msg = f"Unknown agent provider: {provider_name}"
    raise ValueError(msg)


def get_available_providers() -> list[str]:
    """Get list of available provider names"""
    return ["agno"]  # Future: ["agno", "crewai", "autogen"]
