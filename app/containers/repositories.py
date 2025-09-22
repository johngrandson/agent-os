from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Singleton

from app.agents.repositories.agent_repository import AgentRepository
from app.knowledge.repositories.knowledge_repository import KnowledgeRepository


class RepositoriesContainer(DeclarativeContainer):
    """All repository implementations"""

    # Repositories - session injection will be handled by main container
    agent_repository = Singleton(AgentRepository)
    knowledge_repository = Singleton(KnowledgeRepository)
