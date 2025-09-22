from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Singleton

from app.agents.repositories.agent_repository import AgentRepository
from app.knowledge.repositories.knowledge_repository import KnowledgeRepository
from app.tasks.repositories.task_repository import TaskRepository
from app.teams.repositories.team_repository import TeamRepository


class RepositoriesContainer(DeclarativeContainer):
    """All repository implementations"""

    # Repositories - session injection will be handled by main container
    agent_repository = Singleton(AgentRepository)
    knowledge_repository = Singleton(KnowledgeRepository)
    task_repository = Singleton(TaskRepository)
    team_repository = Singleton(TeamRepository)
