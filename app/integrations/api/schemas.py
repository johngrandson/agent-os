"""
API schemas for external integrations
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class IntegrationTypeSchema(str, Enum):
    """Integration types"""

    REST_API = "rest_api"
    WEBHOOK = "webhook"
    OAUTH = "oauth"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    FILE_STORAGE = "file_storage"
    NOTIFICATION = "notification"
    AI_SERVICE = "ai_service"


class AuthTypeSchema(str, Enum):
    """Authentication types"""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class CreateIntegrationRequest(BaseModel):
    """Request to create a new integration"""

    name: str = Field(..., description="Integration name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Integration description")
    integration_type: IntegrationTypeSchema = Field(
        ..., description="Type of integration"
    )
    base_url: str = Field(..., description="Base URL for the integration")
    auth_type: AuthTypeSchema = Field(
        AuthTypeSchema.NONE, description="Authentication type"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        None, description="Authentication credentials"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Integration-specific settings"
    )
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=300)


class UpdateIntegrationRequest(BaseModel):
    """Request to update an integration"""

    name: Optional[str] = Field(
        None, description="Integration name", min_length=1, max_length=255
    )
    description: Optional[str] = Field(None, description="Integration description")
    base_url: Optional[str] = Field(None, description="Base URL for the integration")
    auth_type: Optional[AuthTypeSchema] = Field(None, description="Authentication type")
    credentials: Optional[Dict[str, Any]] = Field(
        None, description="Authentication credentials"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Integration-specific settings"
    )
    timeout: Optional[int] = Field(
        None, description="Request timeout in seconds", ge=1, le=300
    )
    is_active: Optional[bool] = Field(None, description="Whether integration is active")


class IntegrationStatsSchema(BaseModel):
    """Integration statistics"""

    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_execution_time: float = Field(
        ..., description="Average execution time in seconds"
    )
    max_execution_time: float = Field(
        ..., description="Maximum execution time in seconds"
    )
    period_hours: int = Field(..., description="Time period for statistics in hours")


class IntegrationResponse(BaseModel):
    """Integration response"""

    id: str = Field(..., description="Integration ID")
    name: str = Field(..., description="Integration name")
    description: Optional[str] = Field(None, description="Integration description")
    integration_type: str = Field(..., description="Integration type")
    base_url: str = Field(..., description="Base URL")
    auth_type: str = Field(..., description="Authentication type")
    is_active: bool = Field(..., description="Whether integration is active")
    timeout: int = Field(..., description="Request timeout in seconds")
    settings: Dict[str, Any] = Field(..., description="Integration settings")
    health_status: Optional[str] = Field(None, description="Health status")
    health_message: Optional[str] = Field(None, description="Health check message")
    last_health_check: Optional[str] = Field(
        None, description="Last health check timestamp"
    )
    stats: Optional[IntegrationStatsSchema] = Field(
        None, description="Integration statistics"
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class IntegrationListResponse(BaseModel):
    """Integration list response"""

    integrations: List[IntegrationResponse] = Field(
        ..., description="List of integrations"
    )
    total_count: int = Field(..., description="Total number of integrations")


class ExecuteRequestRequest(BaseModel):
    """Request to execute an integration request"""

    method: str = Field(
        ..., description="HTTP method", pattern="^(GET|POST|PUT|PATCH|DELETE)$"
    )
    endpoint: str = Field(..., description="API endpoint")
    data: Optional[Dict[str, Any]] = Field(None, description="Request data")
    headers: Optional[Dict[str, str]] = Field(None, description="Request headers")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")


class ExecuteRequestResponse(BaseModel):
    """Response from integration request execution"""

    success: bool = Field(..., description="Whether request was successful")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    data: Any = Field(None, description="Response data")
    headers: Dict[str, str] = Field(..., description="Response headers")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )


class TestConnectionResponse(BaseModel):
    """Response from connection test"""

    success: bool = Field(..., description="Whether connection test was successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: Optional[float] = Field(
        None, description="Test execution time in seconds"
    )
    timestamp: str = Field(..., description="Test timestamp")


class IntegrationLogResponse(BaseModel):
    """Integration log response"""

    id: str = Field(..., description="Log entry ID")
    method: str = Field(..., description="HTTP method")
    endpoint: str = Field(..., description="API endpoint")
    success: bool = Field(..., description="Whether request was successful")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    triggered_by: Optional[str] = Field(None, description="What triggered this request")
    created_at: str = Field(..., description="Request timestamp")


class IntegrationLogsResponse(BaseModel):
    """Integration logs response"""

    logs: List[IntegrationLogResponse] = Field(..., description="List of log entries")
    total_count: int = Field(..., description="Total number of log entries")


class CreateWebhookRequest(BaseModel):
    """Request to create a webhook endpoint"""

    integration_id: str = Field(..., description="Integration ID")
    endpoint_path: str = Field(..., description="Webhook endpoint path")
    webhook_secret: Optional[str] = Field(
        None, description="Webhook secret for signature verification"
    )
    expected_content_type: str = Field(
        "application/json", description="Expected content type"
    )
    event_mapping: Optional[Dict[str, Any]] = Field(
        None, description="Event mapping configuration"
    )
    transformation_rules: Optional[Dict[str, Any]] = Field(
        None, description="Data transformation rules"
    )


class WebhookResponse(BaseModel):
    """Webhook endpoint response"""

    id: str = Field(..., description="Webhook ID")
    integration_id: str = Field(..., description="Integration ID")
    endpoint_path: str = Field(..., description="Webhook endpoint path")
    expected_content_type: str = Field(..., description="Expected content type")
    is_active: bool = Field(..., description="Whether webhook is active")
    total_received: int = Field(..., description="Total webhooks received")
    last_received: Optional[str] = Field(
        None, description="Last webhook received timestamp"
    )
    created_at: str = Field(..., description="Creation timestamp")


class WebhookListResponse(BaseModel):
    """Webhook list response"""

    webhooks: List[WebhookResponse] = Field(..., description="List of webhooks")
    total_count: int = Field(..., description="Total number of webhooks")
