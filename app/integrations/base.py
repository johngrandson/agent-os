"""
Base classes for external API integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Types of external integrations"""

    REST_API = "rest_api"
    WEBHOOK = "webhook"
    OAUTH = "oauth"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    FILE_STORAGE = "file_storage"
    NOTIFICATION = "notification"
    AI_SERVICE = "ai_service"


class AuthType(str, Enum):
    """Authentication types for integrations"""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


@dataclass
class IntegrationCredential:
    """Credential information for external integrations"""

    auth_type: AuthType
    credentials: Dict[str, Any]
    expires_at: Optional[str] = None
    refresh_token: Optional[str] = None


@dataclass
class IntegrationConfig:
    """Configuration for external integrations"""

    id: str
    name: str
    integration_type: IntegrationType
    base_url: str
    credential: IntegrationCredential
    settings: Dict[str, Any]
    is_active: bool = True
    rate_limit: Optional[Dict[str, Any]] = None
    timeout: int = 30
    retry_config: Optional[Dict[str, Any]] = None


class IntegrationResult:
    """Result of an integration operation"""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        execution_time: Optional[float] = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.status_code = status_code
        self.headers = headers or {}
        self.execution_time = execution_time

    def __repr__(self):
        return (
            f"IntegrationResult(success={self.success}, status_code={self.status_code})"
        )


class BaseIntegration(ABC):
    """Base class for all external integrations"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.id = config.id
        self.name = config.name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def validate_connection(self) -> IntegrationResult:
        """Validate that the integration can connect to the external service"""
        pass

    @abstractmethod
    async def execute_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> IntegrationResult:
        """Execute a request to the external service"""
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on credential configuration"""
        headers = {}
        credential = self.config.credential

        if credential.auth_type == AuthType.API_KEY:
            # API key can be in header or query param
            key_name = credential.credentials.get("key_name", "X-API-Key")
            api_key = credential.credentials.get("api_key")
            if api_key:
                headers[key_name] = api_key

        elif credential.auth_type == AuthType.BEARER_TOKEN:
            token = credential.credentials.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif credential.auth_type == AuthType.BASIC_AUTH:
            import base64

            username = credential.credentials.get("username")
            password = credential.credentials.get("password")
            if username and password:
                auth_string = f"{username}:{password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_auth}"

        return headers

    def is_rate_limited(self) -> bool:
        """Check if integration should be rate limited"""
        # Implementation would check rate limiting rules
        return False

    async def refresh_credentials(self) -> bool:
        """Refresh expired credentials if possible"""
        # Override in subclasses that support credential refresh
        return False

    def __str__(self):
        return f"{self.__class__.__name__}({self.name})"


class RestApiIntegration(BaseIntegration):
    """REST API integration implementation"""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.session = None

    async def _get_session(self):
        """Get or create HTTP session"""
        if not self.session:
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def validate_connection(self) -> IntegrationResult:
        """Validate connection by making a test request"""
        try:
            # Use health endpoint if configured, otherwise try a GET to base URL
            health_endpoint = self.config.settings.get("health_endpoint", "/health")
            result = await self.execute_request("GET", health_endpoint)

            if result.success or result.status_code in [
                200,
                404,
            ]:  # 404 is ok for health check
                return IntegrationResult(success=True, data="Connection validated")
            else:
                return IntegrationResult(
                    success=False, error=f"Connection failed: {result.error}"
                )

        except Exception as e:
            return IntegrationResult(
                success=False, error=f"Connection validation failed: {str(e)}"
            )

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> IntegrationResult:
        """Execute HTTP request to the external API"""
        import time

        start_time = time.time()

        try:
            session = await self._get_session()

            # Build URL
            url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

            # Prepare headers
            request_headers = self.get_auth_headers()
            if headers:
                request_headers.update(headers)

            # Add content type for POST/PUT requests
            if method.upper() in ["POST", "PUT", "PATCH"] and data:
                request_headers.setdefault("Content-Type", "application/json")

            self.logger.info(f"Making {method} request to {url}")

            # Make request
            async with session.request(
                method=method.upper(),
                url=url,
                json=data if data else None,
                headers=request_headers,
                params=params,
            ) as response:
                execution_time = time.time() - start_time
                response_data = None

                # Try to parse JSON response
                try:
                    if response.content_type == "application/json":
                        response_data = await response.json()
                    else:
                        response_data = await response.text()
                except Exception:
                    response_data = await response.text()

                # Determine success
                success = 200 <= response.status < 300

                return IntegrationResult(
                    success=success,
                    data=response_data,
                    status_code=response.status,
                    headers=dict(response.headers),
                    execution_time=execution_time,
                    error=None
                    if success
                    else f"HTTP {response.status}: {response_data}",
                )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Request failed: {str(e)}")
            return IntegrationResult(
                success=False, error=str(e), execution_time=execution_time
            )

    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


class WebhookIntegration(BaseIntegration):
    """Webhook integration for receiving external events"""

    async def validate_connection(self) -> IntegrationResult:
        """Validate webhook configuration"""
        webhook_url = self.config.settings.get("webhook_url")
        if not webhook_url:
            return IntegrationResult(success=False, error="Webhook URL not configured")

        secret = self.config.settings.get("webhook_secret")
        if not secret:
            self.logger.warning("Webhook secret not configured - security risk")

        return IntegrationResult(success=True, data="Webhook configuration valid")

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> IntegrationResult:
        """Webhooks are receive-only, so this registers a webhook endpoint"""
        return IntegrationResult(
            success=False, error="Webhooks are receive-only integrations"
        )

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature"""
        import hmac
        import hashlib

        secret = self.config.settings.get("webhook_secret")
        if not secret:
            return True  # No secret configured, accept all

        expected_signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class IntegrationRegistry:
    """Registry for managing external integrations"""

    def __init__(self):
        self.integrations: Dict[str, BaseIntegration] = {}
        self.integration_types: Dict[IntegrationType, type] = {
            IntegrationType.REST_API: RestApiIntegration,
            IntegrationType.WEBHOOK: WebhookIntegration,
        }

    def register_integration_type(self, integration_type: IntegrationType, cls: type):
        """Register a new integration type"""
        self.integration_types[integration_type] = cls

    def create_integration(self, config: IntegrationConfig) -> BaseIntegration:
        """Create an integration instance from configuration"""
        integration_cls = self.integration_types.get(config.integration_type)
        if not integration_cls:
            raise ValueError(f"Unsupported integration type: {config.integration_type}")

        integration = integration_cls(config)
        self.integrations[config.id] = integration
        return integration

    def get_integration(self, integration_id: str) -> Optional[BaseIntegration]:
        """Get integration by ID"""
        return self.integrations.get(integration_id)

    def list_integrations(self) -> List[BaseIntegration]:
        """List all registered integrations"""
        return list(self.integrations.values())

    def remove_integration(self, integration_id: str) -> bool:
        """Remove an integration"""
        if integration_id in self.integrations:
            integration = self.integrations[integration_id]
            if hasattr(integration, "close"):
                # Close any open connections
                import asyncio

                try:
                    asyncio.create_task(integration.close())
                except Exception:
                    pass
            del self.integrations[integration_id]
            return True
        return False


# Global registry instance
integration_registry = IntegrationRegistry()
