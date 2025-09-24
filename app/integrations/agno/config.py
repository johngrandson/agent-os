"""Agno integration configuration"""

from collections.abc import Callable
from dataclasses import dataclass

from app.agents.agent import Agent


@dataclass
class AgnoConversionConfig:
    """Configuration for converting agents to AgnoAgent instances"""

    # AgnoAgent behavior configuration
    search_knowledge: bool = True
    add_history_to_context: bool = True
    num_history_runs: int = 3
    add_datetime_to_context: bool = True
    markdown: bool = False

    # Agent filtering
    agent_filter: Callable[[Agent], bool] | None = None

    # Error handling
    continue_on_error: bool = False

    @staticmethod
    def for_webhook() -> "AgnoConversionConfig":
        """Configuration optimized for webhook processing"""
        return AgnoConversionConfig(
            markdown=True,  # WhatsApp supports markdown
            continue_on_error=True,  # Don't fail if one agent fails
            agent_filter=lambda agent: agent.whatsapp_enabled and bool(agent.whatsapp_token),
        )

    @staticmethod
    def for_agent_os() -> "AgnoConversionConfig":
        """Configuration optimized for AgentOS integration"""
        return AgnoConversionConfig(
            markdown=False,  # AgentOS doesn't need markdown
            continue_on_error=False,  # Fail fast for AgentOS
            agent_filter=None,  # Load all active agents
        )

    @staticmethod
    def default() -> "AgnoConversionConfig":
        """Default configuration"""
        return AgnoConversionConfig()
