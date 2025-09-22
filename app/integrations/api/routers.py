"""
API routes for external integrations
"""

import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from dependency_injector.wiring import inject, Provide

from app.integrations.api.schemas import (
    CreateIntegrationRequest,
    UpdateIntegrationRequest,
    IntegrationResponse,
    IntegrationListResponse,
    ExecuteRequestRequest,
    ExecuteRequestResponse,
    TestConnectionResponse,
    IntegrationLogResponse,
    IntegrationLogsResponse,
    CreateWebhookRequest,
    WebhookResponse,
    WebhookListResponse,
)
from app.integrations.base import IntegrationType, AuthType
from app.integrations.services import integration_service
from app.container import ApplicationContainer as Container

router = APIRouter(tags=["integrations"])


@router.post(
    "/integrations",
    response_model=IntegrationResponse,
    summary="Create integration",
    description="Create a new external integration",
)
@inject
async def create_integration(
    request: CreateIntegrationRequest,
    container: Container = Depends(Provide[Container]),
):
    """Create a new external integration"""
    try:
        result = await integration_service.create_integration(
            name=request.name,
            integration_type=IntegrationType(request.integration_type),
            base_url=request.base_url,
            auth_type=AuthType(request.auth_type),
            credentials=request.credentials,
            settings=request.settings,
            timeout=request.timeout,
        )
        return IntegrationResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create integration: {str(e)}"
        )


@router.get(
    "/integrations",
    response_model=IntegrationListResponse,
    summary="List integrations",
    description="Get list of all integrations",
)
async def list_integrations(
    integration_type: Optional[str] = Query(
        None, description="Filter by integration type"
    ),
    active_only: bool = Query(False, description="Show only active integrations"),
):
    """Get list of all integrations"""
    try:
        integrations = await integration_service.list_integrations(
            integration_type=integration_type, active_only=active_only
        )

        return IntegrationListResponse(
            integrations=[
                IntegrationResponse(**integration) for integration in integrations
            ],
            total_count=len(integrations),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list integrations: {str(e)}"
        )


@router.get(
    "/integrations/{integration_id}",
    response_model=IntegrationResponse,
    summary="Get integration",
    description="Get integration details by ID",
)
async def get_integration(integration_id: str):
    """Get integration details by ID"""
    try:
        integration_uuid = uuid.UUID(integration_id)
        integration = await integration_service.get_integration(integration_uuid)

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        return IntegrationResponse(**integration)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get integration: {str(e)}"
        )


@router.put(
    "/integrations/{integration_id}",
    response_model=IntegrationResponse,
    summary="Update integration",
    description="Update integration configuration",
)
async def update_integration(integration_id: str, request: UpdateIntegrationRequest):
    """Update integration configuration"""
    try:
        integration_uuid = uuid.UUID(integration_id)

        # Convert request to dict, excluding None values
        updates = request.dict(exclude_unset=True, exclude_none=True)

        # Convert enum values to strings
        if "auth_type" in updates:
            updates["auth_type"] = updates["auth_type"].value

        integration = await integration_service.update_integration(
            integration_uuid, updates
        )

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        return IntegrationResponse(**integration)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update integration: {str(e)}"
        )


@router.delete(
    "/integrations/{integration_id}",
    summary="Delete integration",
    description="Delete an integration",
)
async def delete_integration(integration_id: str):
    """Delete an integration"""
    try:
        integration_uuid = uuid.UUID(integration_id)
        deleted = await integration_service.delete_integration(integration_uuid)

        if not deleted:
            raise HTTPException(status_code=404, detail="Integration not found")

        return {"message": "Integration deleted successfully"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete integration: {str(e)}"
        )


@router.post(
    "/integrations/{integration_id}/test",
    response_model=TestConnectionResponse,
    summary="Test integration",
    description="Test integration connection",
)
async def test_integration(integration_id: str):
    """Test integration connection"""
    try:
        integration_uuid = uuid.UUID(integration_id)
        result = await integration_service.test_integration(integration_uuid)
        return TestConnectionResponse(**result)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to test integration: {str(e)}"
        )


@router.post(
    "/integrations/{integration_id}/execute",
    response_model=ExecuteRequestResponse,
    summary="Execute request",
    description="Execute a request through the integration",
)
async def execute_request(
    integration_id: str,
    request: ExecuteRequestRequest,
    triggered_by: Optional[str] = Query(
        None, description="What triggered this request"
    ),
):
    """Execute a request through the integration"""
    try:
        integration_uuid = uuid.UUID(integration_id)

        result = await integration_service.execute_integration_request(
            integration_id=integration_uuid,
            method=request.method,
            endpoint=request.endpoint,
            data=request.data,
            headers=request.headers,
            params=request.params,
            triggered_by=triggered_by,
        )

        return ExecuteRequestResponse(
            success=result.success,
            status_code=result.status_code,
            data=result.data,
            headers=result.headers,
            error=result.error,
            execution_time=result.execution_time,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to execute request: {str(e)}"
        )


@router.get(
    "/integrations/{integration_id}/logs",
    response_model=IntegrationLogsResponse,
    summary="Get integration logs",
    description="Get logs for an integration",
)
async def get_integration_logs(
    integration_id: str,
    limit: int = Query(100, description="Maximum number of logs", ge=1, le=1000),
    success_only: Optional[bool] = Query(None, description="Filter by success status"),
):
    """Get logs for an integration"""
    try:
        integration_uuid = uuid.UUID(integration_id)

        logs = await integration_service.get_integration_logs(
            integration_uuid, limit=limit, success_only=success_only
        )

        return IntegrationLogsResponse(
            logs=[IntegrationLogResponse(**log) for log in logs], total_count=len(logs)
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid integration ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get integration logs: {str(e)}"
        )


@router.get(
    "/integrations/types",
    response_model=List[str],
    summary="Get integration types",
    description="Get list of available integration types",
)
async def get_integration_types():
    """Get list of available integration types"""
    return [integration_type.value for integration_type in IntegrationType]


@router.get(
    "/integrations/auth-types",
    response_model=List[str],
    summary="Get auth types",
    description="Get list of available authentication types",
)
async def get_auth_types():
    """Get list of available authentication types"""
    return [auth_type.value for auth_type in AuthType]
