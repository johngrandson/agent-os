"""
Database models for external integrations
"""

import uuid
from typing import Dict, Any
from sqlalchemy import String, Text, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base
from infrastructure.database.mixins.timestamp_mixin import TimestampMixin


class Integration(Base, TimestampMixin):
    """External integration configuration"""

    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    integration_type: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Authentication configuration
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    credentials: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Integration settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Status and configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout: Mapped[int] = mapped_column(Integer, default=30)

    # Rate limiting and retry configuration
    rate_limit_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    retry_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Health monitoring
    last_health_check: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    health_status: Mapped[str] = mapped_column(String(50), nullable=True)
    health_message: Mapped[str] = mapped_column(Text, nullable=True)


class IntegrationLog(Base, TimestampMixin):
    """Log of integration requests and responses"""

    __tablename__ = "integration_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Request details
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    request_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    request_headers: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Response details
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    response_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    response_headers: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Performance metrics
    execution_time: Mapped[float] = mapped_column(nullable=True)

    # Context
    triggered_by: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # agent_id, task_id, etc.
    context: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)


class WebhookEndpoint(Base, TimestampMixin):
    """Webhook endpoint configuration"""

    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Webhook configuration
    endpoint_path: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_secret: Mapped[str] = mapped_column(String(255), nullable=True)
    expected_content_type: Mapped[str] = mapped_column(
        String(100), default="application/json"
    )

    # Processing configuration
    event_mapping: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    transformation_rules: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_received: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    total_received: Mapped[int] = mapped_column(Integer, default=0)


class WebhookDelivery(Base, TimestampMixin):
    """Log of received webhook deliveries"""

    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Delivery details
    headers: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=True)

    # Processing results
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Events generated
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    processing_time: Mapped[float] = mapped_column(nullable=True)
