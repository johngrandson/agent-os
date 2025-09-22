"""
Task repository for database operations
"""

import uuid
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from infrastructure.database.session import get_session
from app.tasks.task import Task, TaskStatus, TaskPriority, TaskType


class TaskRepository:
    """Repository for task database operations"""

    async def save(self, *, task: Task) -> Task:
        """Save a task to the database"""
        async with get_session() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def update(self, *, task: Task) -> Task:
        """Update a task in the database"""
        async with get_session() as session:
            await session.merge(task)
            await session.commit()
            return task

    async def delete(self, *, task: Task) -> None:
        """Delete a task from the database"""
        async with get_session() as session:
            await session.delete(task)
            await session.commit()

    async def get_task_by_id(self, *, task_id: uuid.UUID) -> Optional[Task]:
        """Get a task by ID"""
        async with get_session() as session:
            result = await session.execute(
                select(Task)
                .options(selectinload(Task.assigned_agent))
                .options(selectinload(Task.subtasks))
                .where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_tasks(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        task_type: Optional[TaskType] = None,
        assigned_agent_id: Optional[uuid.UUID] = None,
        assigned_by: Optional[str] = None,
        include_subtasks: bool = True,
    ) -> List[Task]:
        """Get tasks with optional filtering"""
        async with get_session() as session:
            query = select(Task).options(selectinload(Task.assigned_agent))

            # Add filters
            filters = []
            if status:
                filters.append(Task.status == status)
            if priority:
                filters.append(Task.priority == priority)
            if task_type:
                filters.append(Task.task_type == task_type)
            if assigned_agent_id:
                filters.append(Task.assigned_agent_id == assigned_agent_id)
            if assigned_by:
                filters.append(Task.assigned_by == assigned_by)
            if not include_subtasks:
                filters.append(Task.parent_task_id.is_(None))

            if filters:
                query = query.where(and_(*filters))

            # Add pagination
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_tasks_by_agent(
        self,
        *,
        agent_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """Get tasks assigned to a specific agent"""
        return await self.get_tasks(
            limit=limit, offset=offset, status=status, assigned_agent_id=agent_id
        )

    async def get_subtasks(
        self, *, parent_task_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> List[Task]:
        """Get subtasks of a parent task"""
        async with get_session() as session:
            result = await session.execute(
                select(Task)
                .options(selectinload(Task.assigned_agent))
                .where(Task.parent_task_id == parent_task_id)
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_pending_tasks(
        self, *, limit: int = 20, priority: Optional[TaskPriority] = None
    ) -> List[Task]:
        """Get pending tasks, optionally filtered by priority"""
        filters = [Task.status == TaskStatus.PENDING]
        if priority:
            filters.append(Task.priority == priority)

        return await self.get_tasks(
            limit=limit,
            status=TaskStatus.PENDING,
            priority=priority,
            include_subtasks=False,
        )

    async def get_active_tasks(
        self, *, agent_id: Optional[uuid.UUID] = None, limit: int = 20
    ) -> List[Task]:
        """Get currently active (in progress) tasks"""
        return await self.get_tasks(
            limit=limit, status=TaskStatus.IN_PROGRESS, assigned_agent_id=agent_id
        )

    async def count_tasks(
        self,
        *,
        status: Optional[TaskStatus] = None,
        assigned_agent_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Count tasks with optional filtering"""
        async with get_session() as session:
            query = select(Task.id)

            filters = []
            if status:
                filters.append(Task.status == status)
            if assigned_agent_id:
                filters.append(Task.assigned_agent_id == assigned_agent_id)

            if filters:
                query = query.where(and_(*filters))

            result = await session.execute(query)
            return len(list(result.scalars().all()))

    async def get_task_statistics(self) -> dict:
        """Get task statistics"""
        async with get_session() as session:
            # Count by status
            status_counts = {}
            for status in TaskStatus:
                result = await session.execute(
                    select(Task.id).where(Task.status == status)
                )
                status_counts[status.value] = len(list(result.scalars().all()))

            # Count by priority
            priority_counts = {}
            for priority in TaskPriority:
                result = await session.execute(
                    select(Task.id).where(Task.priority == priority)
                )
                priority_counts[priority.value] = len(list(result.scalars().all()))

            # Count by type
            type_counts = {}
            for task_type in TaskType:
                result = await session.execute(
                    select(Task.id).where(Task.task_type == task_type)
                )
                type_counts[task_type.value] = len(list(result.scalars().all()))

            return {
                "by_status": status_counts,
                "by_priority": priority_counts,
                "by_type": type_counts,
            }
