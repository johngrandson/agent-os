"""
Repositories for external integrations
"""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.models import (
    Integration,
    IntegrationLog,
    WebhookEndpoint,
    WebhookDelivery,
)
from infrastructure.database.session import get_session


class IntegrationRepository:
    """Repository for integration management"""

    async def create(self, integration_data: Dict[str, Any]) -> Integration:
        """Create a new integration"""
        async with get_session() as session:
            integration = Integration(**integration_data)
            session.add(integration)
            await session.commit()
            await session.refresh(integration)
            return integration

    async def get_by_id(self, integration_id: uuid.UUID) -> Optional[Integration]:
        """Get integration by ID"""
        async with get_session() as session:
            result = await session.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Integration]:
        """Get integration by name"""
        async with get_session() as session:
            result = await session.execute(
                select(Integration).where(Integration.name == name)
            )
            return result.scalar_one_or_none()

    async def list_all(self, active_only: bool = False) -> List[Integration]:
        """List all integrations"""
        async with get_session() as session:
            query = select(Integration)
            if active_only:
                query = query.where(Integration.is_active == True)
            query = query.order_by(Integration.name)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def list_by_type(
        self, integration_type: str, active_only: bool = False
    ) -> List[Integration]:
        """List integrations by type"""
        async with get_session() as session:
            query = select(Integration).where(
                Integration.integration_type == integration_type
            )
            if active_only:
                query = query.where(Integration.is_active == True)
            query = query.order_by(Integration.name)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def update(
        self, integration_id: uuid.UUID, updates: Dict[str, Any]
    ) -> Optional[Integration]:
        """Update an integration"""
        async with get_session() as session:
            await session.execute(
                update(Integration)
                .where(Integration.id == integration_id)
                .values(**updates)
            )
            await session.commit()

            # Return updated integration
            result = await session.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            return result.scalar_one_or_none()

    async def delete(self, integration_id: uuid.UUID) -> bool:
        """Delete an integration"""
        async with get_session() as session:
            result = await session.execute(
                delete(Integration).where(Integration.id == integration_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def update_health_status(
        self, integration_id: uuid.UUID, status: str, message: Optional[str] = None
    ):
        """Update integration health status"""
        from datetime import datetime

        updates = {"last_health_check": datetime.utcnow(), "health_status": status}
        if message:
            updates["health_message"] = message

        await self.update(integration_id, updates)


class IntegrationLogRepository:
    """Repository for integration logs"""

    async def create_log(self, log_data: Dict[str, Any]) -> IntegrationLog:
        """Create a new integration log entry"""
        async with get_session() as session:
            log_entry = IntegrationLog(**log_data)
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            return log_entry

    async def get_logs_for_integration(
        self,
        integration_id: uuid.UUID,
        limit: int = 100,
        success_only: Optional[bool] = None,
    ) -> List[IntegrationLog]:
        """Get logs for a specific integration"""
        async with get_session() as session:
            query = select(IntegrationLog).where(
                IntegrationLog.integration_id == integration_id
            )

            if success_only is not None:
                query = query.where(IntegrationLog.success == success_only)

            query = query.order_by(desc(IntegrationLog.created_at)).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_recent_logs(
        self, limit: int = 100, hours: int = 24
    ) -> List[IntegrationLog]:
        """Get recent logs across all integrations"""
        from datetime import datetime, timedelta

        async with get_session() as session:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = (
                select(IntegrationLog)
                .where(IntegrationLog.created_at >= since)
                .order_by(desc(IntegrationLog.created_at))
                .limit(limit)
            )

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_error_logs(
        self, integration_id: Optional[uuid.UUID] = None, limit: int = 50
    ) -> List[IntegrationLog]:
        """Get error logs"""
        async with get_session() as session:
            query = select(IntegrationLog).where(IntegrationLog.success == False)

            if integration_id:
                query = query.where(IntegrationLog.integration_id == integration_id)

            query = query.order_by(desc(IntegrationLog.created_at)).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_integration_stats(
        self, integration_id: uuid.UUID, hours: int = 24
    ) -> Dict[str, Any]:
        """Get statistics for an integration"""
        from datetime import datetime, timedelta
        from sqlalchemy import func

        async with get_session() as session:
            since = datetime.utcnow() - timedelta(hours=hours)

            # Get basic stats
            result = await session.execute(
                select(
                    func.count(IntegrationLog.id).label("total_requests"),
                    func.count(IntegrationLog.id)
                    .filter(IntegrationLog.success == True)
                    .label("successful_requests"),
                    func.count(IntegrationLog.id)
                    .filter(IntegrationLog.success == False)
                    .label("failed_requests"),
                    func.avg(IntegrationLog.execution_time).label("avg_execution_time"),
                    func.max(IntegrationLog.execution_time).label("max_execution_time"),
                ).where(
                    and_(
                        IntegrationLog.integration_id == integration_id,
                        IntegrationLog.created_at >= since,
                    )
                )
            )

            stats = result.first()

            return {
                "total_requests": stats.total_requests or 0,
                "successful_requests": stats.successful_requests or 0,
                "failed_requests": stats.failed_requests or 0,
                "success_rate": (
                    (stats.successful_requests / stats.total_requests * 100)
                    if stats.total_requests > 0
                    else 0
                ),
                "avg_execution_time": float(stats.avg_execution_time or 0),
                "max_execution_time": float(stats.max_execution_time or 0),
                "period_hours": hours,
            }


class WebhookRepository:
    """Repository for webhook management"""

    async def create_endpoint(self, endpoint_data: Dict[str, Any]) -> WebhookEndpoint:
        """Create a new webhook endpoint"""
        async with get_session() as session:
            endpoint = WebhookEndpoint(**endpoint_data)
            session.add(endpoint)
            await session.commit()
            await session.refresh(endpoint)
            return endpoint

    async def get_endpoint_by_path(self, path: str) -> Optional[WebhookEndpoint]:
        """Get webhook endpoint by path"""
        async with get_session() as session:
            result = await session.execute(
                select(WebhookEndpoint).where(
                    and_(
                        WebhookEndpoint.endpoint_path == path,
                        WebhookEndpoint.is_active == True,
                    )
                )
            )
            return result.scalar_one_or_none()

    async def get_endpoints_for_integration(
        self, integration_id: uuid.UUID
    ) -> List[WebhookEndpoint]:
        """Get all webhook endpoints for an integration"""
        async with get_session() as session:
            result = await session.execute(
                select(WebhookEndpoint)
                .where(WebhookEndpoint.integration_id == integration_id)
                .order_by(WebhookEndpoint.endpoint_path)
            )
            return list(result.scalars().all())

    async def create_delivery(self, delivery_data: Dict[str, Any]) -> WebhookDelivery:
        """Create a new webhook delivery record"""
        async with get_session() as session:
            delivery = WebhookDelivery(**delivery_data)
            session.add(delivery)
            await session.commit()
            await session.refresh(delivery)
            return delivery

    async def update_endpoint_stats(
        self, endpoint_id: uuid.UUID, increment_total: bool = True
    ):
        """Update webhook endpoint statistics"""
        from datetime import datetime

        async with get_session() as session:
            updates = {"last_received": datetime.utcnow()}
            if increment_total:
                # This requires a more complex update with increment
                result = await session.execute(
                    select(WebhookEndpoint.total_received).where(
                        WebhookEndpoint.id == endpoint_id
                    )
                )
                current_total = result.scalar_one_or_none() or 0
                updates["total_received"] = current_total + 1

            await session.execute(
                update(WebhookEndpoint)
                .where(WebhookEndpoint.id == endpoint_id)
                .values(**updates)
            )
            await session.commit()

    async def get_recent_deliveries(
        self, endpoint_id: Optional[uuid.UUID] = None, limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get recent webhook deliveries"""
        async with get_session() as session:
            query = select(WebhookDelivery)

            if endpoint_id:
                query = query.where(WebhookDelivery.webhook_endpoint_id == endpoint_id)

            query = query.order_by(desc(WebhookDelivery.created_at)).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())


# Repository instances
integration_repository = IntegrationRepository()
integration_log_repository = IntegrationLogRepository()
webhook_repository = WebhookRepository()
