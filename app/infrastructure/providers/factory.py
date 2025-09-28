"""
Simple provider factory for environment-based provider selection.
Following CLAUDE.md: boring over clever, single responsibility.
"""

import os
from typing import TYPE_CHECKING

from app.infrastructure.providers.base import AgentProvider, RuntimeAgent
from core.logger import get_module_logger


if TYPE_CHECKING:
    from app.infrastructure.cache import SemanticCacheService
    from core.config import Config


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
        from app.infrastructure.providers.agno import AgnoProvider

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


def create_cache_wrapper_factory(
    cache_service: "SemanticCacheService",
    config: "Config",
) -> callable:
    """
    Create a cache wrapper factory function.

    Args:
        cache_service: Semantic cache service for caching
        config: Configuration for cache settings

    Returns:
        A function that takes runtime_agents and returns cached agents
    """

    def wrapper(runtime_agents: list[RuntimeAgent]) -> list[RuntimeAgent]:
        return wrap_runtime_agents_with_cache(runtime_agents, cache_service, config)

    return wrapper


def wrap_runtime_agents_with_cache(
    runtime_agents: list[RuntimeAgent],
    cache_service: "SemanticCacheService",
    config: "Config",
) -> list[RuntimeAgent]:
    """
    Wrap runtime agents with semantic cache if enabled.

    Args:
        runtime_agents: List of runtime agents to potentially wrap
        cache_service: Semantic cache service for caching
        config: Configuration for cache settings

    Returns:
        List of potentially cached runtime agents
    """
    # Check if cache integration is enabled
    if not config.CACHE_AI_PROVIDERS_ENABLED or not config.CACHE_ENABLED:
        logger.info("AI provider cache integration disabled")
        return runtime_agents

    try:
        from app.infrastructure.cache.middleware.cached_provider import CachedRuntimeAgent

        cached_agents = []
        for agent in runtime_agents:
            cached_agent = CachedRuntimeAgent(
                runtime_agent=agent,
                cache_service=cache_service,
                enable_cache=True,
            )
            cached_agents.append(cached_agent)

        logger.info(f"Wrapped {len(cached_agents)} runtime agents with semantic cache")
        return cached_agents

    except Exception as e:
        logger.warning(f"Failed to wrap agents with cache: {e}. Using original agents.")
        return runtime_agents
