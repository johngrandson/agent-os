"""
Minimal provider interfaces for agent runtime abstraction.
Following CLAUDE.md: boring, simple interfaces that wrap what we actually need.
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import FastAPI


class RuntimeAgent(ABC):
    """Simple wrapper for runtime agents - abstracts the minimum needed interface"""

    @abstractmethod
    async def arun(self, message: str) -> str:
        """Run agent with message, return response"""

    @property
    @abstractmethod
    def id(self) -> str:
        """Agent ID"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name"""


class AgentProvider(ABC):
    """
    Provider interface for converting DB agents to runtime agents.
    Only abstracts what we actually need to switch between providers.
    """

    @abstractmethod
    async def convert_agents_for_webhook(self, db_agents: list[Any]) -> list[RuntimeAgent]:
        """Convert agents for webhook processing with webhook-specific config"""

    @abstractmethod
    async def convert_agents_for_runtime(self, db_agents: list[Any]) -> list[RuntimeAgent]:
        """Convert agents for AgentOS runtime with runtime-specific config"""

    @abstractmethod
    def setup_runtime_with_app(self, runtime_agents: list[RuntimeAgent], app: FastAPI) -> FastAPI:
        """Setup runtime system (like AgentOS) with FastAPI app"""
