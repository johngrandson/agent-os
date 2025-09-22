"""
Services for external integrations
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.integrations.base import (
    IntegrationConfig,
    IntegrationCredential,
    IntegrationType,
    AuthType,
    integration_registry,
    IntegrationResult,
)
from app.integrations.repositories import (
    integration_repository,
    integration_log_repository,
    webhook_repository,
)
from app.events.bus import EventBus
from app.integrations.events import IntegrationEvent

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for managing external integrations"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def create_integration(
        self,
        name: str,
        integration_type: IntegrationType,
        base_url: str,
        auth_type: AuthType = AuthType.NONE,
        credentials: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Create a new integration"""

        try:
            # Check if integration with same name exists
            existing = await integration_repository.get_by_name(name)
            if existing:
                raise ValueError(f"Integration with name '{name}' already exists")

            # Create integration record
            integration_data = {
                "name": name,
                "integration_type": integration_type.value,
                "base_url": base_url,
                "auth_type": auth_type.value,
                "credentials": credentials or {},
                "settings": settings or {},
                "timeout": timeout,
                "is_active": True,
            }

            integration_model = await integration_repository.create(integration_data)

            # Create integration configuration
            credential = IntegrationCredential(
                auth_type=auth_type, credentials=credentials or {}
            )

            config = IntegrationConfig(
                id=str(integration_model.id),
                name=name,
                integration_type=integration_type,
                base_url=base_url,
                credential=credential,
                settings=settings or {},
                timeout=timeout,
            )

            # Register with integration registry
            integration_instance = integration_registry.create_integration(config)

            # Test connection
            validation_result = await integration_instance.validate_connection()

            # Update health status
            await integration_repository.update_health_status(
                integration_model.id,
                "healthy" if validation_result.success else "unhealthy",
                validation_result.error
                if not validation_result.success
                else "Connection validated",
            )

            # Emit event
            await self.event_bus.emit(
                IntegrationEvent.integration_created(
                    integration_id=str(integration_model.id),
                    data={
                        "name": name,
                        "type": integration_type.value,
                        "validation_success": validation_result.success,
                    },
                )
            )

            return {
                "id": str(integration_model.id),
                "name": name,
                "integration_type": integration_type.value,
                "base_url": base_url,
                "is_active": True,
                "validation_result": {
                    "success": validation_result.success,
                    "error": validation_result.error,
                },
                "created_at": integration_model.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create integration '{name}': {str(e)}")
            raise

    async def get_integration(
        self, integration_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get integration by ID"""
        integration_model = await integration_repository.get_by_id(integration_id)
        if not integration_model:
            return None

        # Get recent stats
        stats = await integration_log_repository.get_integration_stats(integration_id)

        return {
            "id": str(integration_model.id),
            "name": integration_model.name,
            "description": integration_model.description,
            "integration_type": integration_model.integration_type,
            "base_url": integration_model.base_url,
            "auth_type": integration_model.auth_type,
            "is_active": integration_model.is_active,
            "timeout": integration_model.timeout,
            "settings": integration_model.settings,
            "health_status": integration_model.health_status,
            "health_message": integration_model.health_message,
            "last_health_check": (
                integration_model.last_health_check.isoformat()
                if integration_model.last_health_check
                else None
            ),
            "stats": stats,
            "created_at": integration_model.created_at.isoformat(),
            "updated_at": integration_model.updated_at.isoformat(),
        }

    async def list_integrations(
        self, integration_type: Optional[str] = None, active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List all integrations"""
        if integration_type:
            integrations = await integration_repository.list_by_type(
                integration_type, active_only
            )
        else:
            integrations = await integration_repository.list_all(active_only)

        result = []
        for integration in integrations:
            result.append(
                {
                    "id": str(integration.id),
                    "name": integration.name,
                    "description": integration.description,
                    "integration_type": integration.integration_type,
                    "base_url": integration.base_url,
                    "is_active": integration.is_active,
                    "health_status": integration.health_status,
                    "last_health_check": (
                        integration.last_health_check.isoformat()
                        if integration.last_health_check
                        else None
                    ),
                    "created_at": integration.created_at.isoformat(),
                }
            )

        return result

    async def update_integration(
        self, integration_id: uuid.UUID, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an integration"""
        try:
            # Update database record
            integration_model = await integration_repository.update(
                integration_id, updates
            )
            if not integration_model:
                return None

            # Update registry if the integration is loaded
            integration_instance = integration_registry.get_integration(
                str(integration_id)
            )
            if integration_instance:
                # Recreate integration with new configuration
                integration_registry.remove_integration(str(integration_id))

                # Create new config
                credential = IntegrationCredential(
                    auth_type=AuthType(integration_model.auth_type),
                    credentials=integration_model.credentials or {},
                )

                config = IntegrationConfig(
                    id=str(integration_model.id),
                    name=integration_model.name,
                    integration_type=IntegrationType(
                        integration_model.integration_type
                    ),
                    base_url=integration_model.base_url,
                    credential=credential,
                    settings=integration_model.settings or {},
                    timeout=integration_model.timeout,
                )

                integration_registry.create_integration(config)

            # Emit event
            await self.event_bus.emit(
                IntegrationEvent.integration_updated(
                    integration_id=str(integration_id),
                    data={"updates": list(updates.keys())},
                )
            )

            return await self.get_integration(integration_id)

        except Exception as e:
            logger.error(f"Failed to update integration {integration_id}: {str(e)}")
            raise

    async def delete_integration(self, integration_id: uuid.UUID) -> bool:
        """Delete an integration"""
        try:
            # Remove from registry
            integration_registry.remove_integration(str(integration_id))

            # Delete from database
            deleted = await integration_repository.delete(integration_id)

            if deleted:
                # Emit event
                await self.event_bus.emit(
                    IntegrationEvent.integration_deleted(
                        integration_id=str(integration_id)
                    )
                )

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete integration {integration_id}: {str(e)}")
            raise

    async def execute_integration_request(
        self,
        integration_id: uuid.UUID,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        triggered_by: Optional[str] = None,
    ) -> IntegrationResult:
        """Execute a request through an integration"""

        integration_instance = integration_registry.get_integration(str(integration_id))
        if not integration_instance:
            # Try to load from database
            integration_model = await integration_repository.get_by_id(integration_id)
            if not integration_model or not integration_model.is_active:
                return IntegrationResult(
                    success=False, error="Integration not found or inactive"
                )

            # Create and register integration
            await self._load_integration(integration_model)
            integration_instance = integration_registry.get_integration(
                str(integration_id)
            )

        try:
            # Execute request
            result = await integration_instance.execute_request(
                method=method,
                endpoint=endpoint,
                data=data,
                headers=headers,
                params=params,
            )

            # Log the request/response
            await self._log_integration_request(
                integration_id=integration_id,
                method=method,
                endpoint=endpoint,
                request_data=data,
                request_headers=headers,
                result=result,
                triggered_by=triggered_by,
            )

            # Emit event
            event_type = (
                "integration.request_success"
                if result.success
                else "integration.request_failed"
            )
            await self.event_bus.emit(
                IntegrationEvent.integration_request(
                    integration_id=str(integration_id),
                    data={
                        "method": method,
                        "endpoint": endpoint,
                        "success": result.success,
                        "status_code": result.status_code,
                        "execution_time": result.execution_time,
                    },
                )
            )

            return result

        except Exception as e:
            logger.error(f"Integration request failed: {str(e)}")
            result = IntegrationResult(success=False, error=str(e))

            # Log the error
            await self._log_integration_request(
                integration_id=integration_id,
                method=method,
                endpoint=endpoint,
                request_data=data,
                request_headers=headers,
                result=result,
                triggered_by=triggered_by,
            )

            return result

    async def test_integration(self, integration_id: uuid.UUID) -> Dict[str, Any]:
        """Test an integration connection"""
        try:
            integration_instance = integration_registry.get_integration(
                str(integration_id)
            )
            if not integration_instance:
                integration_model = await integration_repository.get_by_id(
                    integration_id
                )
                if not integration_model:
                    return {"success": False, "error": "Integration not found"}

                await self._load_integration(integration_model)
                integration_instance = integration_registry.get_integration(
                    str(integration_id)
                )

            # Test connection
            result = await integration_instance.validate_connection()

            # Update health status
            await integration_repository.update_health_status(
                integration_id,
                "healthy" if result.success else "unhealthy",
                result.error if not result.success else "Connection test successful",
            )

            return {
                "success": result.success,
                "error": result.error,
                "execution_time": result.execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Integration test failed: {str(e)}")
            await integration_repository.update_health_status(
                integration_id, "unhealthy", f"Test failed: {str(e)}"
            )
            return {"success": False, "error": str(e)}

    async def get_integration_logs(
        self,
        integration_id: uuid.UUID,
        limit: int = 100,
        success_only: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Get logs for an integration"""
        logs = await integration_log_repository.get_logs_for_integration(
            integration_id, limit, success_only
        )

        return [
            {
                "id": str(log.id),
                "method": log.method,
                "endpoint": log.endpoint,
                "success": log.success,
                "status_code": log.status_code,
                "execution_time": log.execution_time,
                "error_message": log.error_message,
                "triggered_by": log.triggered_by,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]

    async def _load_integration(self, integration_model) -> None:
        """Load an integration from database model"""
        credential = IntegrationCredential(
            auth_type=AuthType(integration_model.auth_type),
            credentials=integration_model.credentials or {},
        )

        config = IntegrationConfig(
            id=str(integration_model.id),
            name=integration_model.name,
            integration_type=IntegrationType(integration_model.integration_type),
            base_url=integration_model.base_url,
            credential=credential,
            settings=integration_model.settings or {},
            timeout=integration_model.timeout,
        )

        integration_registry.create_integration(config)

    async def _log_integration_request(
        self,
        integration_id: uuid.UUID,
        method: str,
        endpoint: str,
        request_data: Optional[Dict[str, Any]],
        request_headers: Optional[Dict[str, str]],
        result: IntegrationResult,
        triggered_by: Optional[str],
    ) -> None:
        """Log an integration request"""
        try:
            log_data = {
                "integration_id": integration_id,
                "method": method,
                "endpoint": endpoint,
                "request_data": request_data,
                "request_headers": request_headers,
                "success": result.success,
                "status_code": result.status_code,
                "response_data": result.data if isinstance(result.data, dict) else None,
                "response_headers": result.headers,
                "error_message": result.error,
                "execution_time": result.execution_time,
                "triggered_by": triggered_by,
            }

            await integration_log_repository.create_log(log_data)

        except Exception as e:
            logger.error(f"Failed to log integration request: {str(e)}")


# Service instances - will be created in container
integration_service = None
