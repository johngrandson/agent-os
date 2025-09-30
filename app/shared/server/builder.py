"""FastAPI application builder for domain-driven server architecture"""

from typing import Any, Self

from app.container import Container
from app.initialization import initialize_database
from app.shared.events import (
    faststream_app,
    setup_broker_with_handlers,
)
from core.config import config
from core.exceptions import CustomException
from core.fastapi.dependencies import Logging
from core.fastapi.middlewares import ResponseLogMiddleware, SQLAlchemyMiddleware
from core.logger import get_module_logger
from core.logging_config import configure_logging
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastapi import APIRouter, Depends, FastAPI, Request


# Configure logging
configure_logging(debug=config.DEBUG)
logger = get_module_logger(__name__)


class FastAPIServerBuilder:
    """Builder for creating FastAPI applications with domain routers"""

    def __init__(self) -> None:
        """Initialize builder with empty router list"""
        self._domain_routers: list[tuple[APIRouter, str]] = []

    def add_domain_router(self, router: APIRouter, prefix: str) -> Self:
        """Add a domain router with its prefix to the builder

        Args:
            router: FastAPI router instance
            prefix: URL prefix for the router (e.g., "/api/v1/agents")

        Returns:
            Self for fluent interface
        """
        self._domain_routers.append((router, prefix))
        return self

    def build(self) -> FastAPI:
        """Build the FastAPI application with all configured functionality

        Returns:
            Fully configured FastAPI application ready for ASGI server
        """
        # Setup dependency injection first
        container = self._setup_dependency_injection()

        # Setup event system
        self._setup_event_system()

        # Get required services from container
        agent_cache = container.agent_cache()
        agent_provider = container.agent_provider()

        # Create FastAPI app with all configuration
        app = self._create_fastapi_app()

        # Setup app components
        self._setup_exception_handlers(app)
        self._setup_health_routes(app)
        self._setup_domain_routes(app)

        # Setup lifecycle events
        self._setup_startup_event(app, agent_cache, agent_provider)
        self._setup_shutdown_event(app)

        return app

    def _setup_dependency_injection(self) -> Container:
        """Configure dependency injection container

        Returns:
            Configured Container instance
        """
        container = Container()
        container.wire(
            modules=[
                "app.domains.agent_management.api.routers",
                "app.domains.communication.webhooks.api.routers",
                "app.domains.evaluation.api.routers",
            ]
        )
        return container

    def _setup_event_system(self) -> None:
        """Configure event system for domain communication"""
        setup_broker_with_handlers()

    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with base configuration

        Returns:
            FastAPI app instance with middleware and dependencies
        """
        return FastAPI(
            title="Agent OS API",
            description="Agent Operating System with integrated AgentOS support",
            version="1.0.0",
            dependencies=[Depends(Logging)],
            middleware=self._create_middlewares(),
        )

    def _create_middlewares(self) -> list[Middleware]:
        """Configure application middlewares

        Returns:
            List of configured middleware instances
        """
        return [
            Middleware(
                CORSMiddleware,
                allow_origins=[
                    "http://localhost:3000",
                    "http://localhost:8080",
                    "http://localhost:8000",
                ],
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["*"],
            ),
            Middleware(SQLAlchemyMiddleware),
            Middleware(ResponseLogMiddleware),
        ]

    def _setup_exception_handlers(self, app: FastAPI) -> None:
        """Configure application exception handlers

        Args:
            app: FastAPI application to configure
        """

        @app.exception_handler(CustomException)
        async def custom_exception_handler(request: Request, exc: CustomException) -> JSONResponse:
            return JSONResponse(
                status_code=exc.code,
                content={"error_code": exc.error_code, "message": exc.message},
            )

    def _setup_health_routes(self, app: FastAPI) -> None:
        """Configure health check routes

        Args:
            app: FastAPI application to configure
        """

        @app.get("/api/v1/health")
        async def health_check() -> dict[str, Any]:
            """Basic health check endpoint"""
            return {
                "status": "healthy",
                "service": "agent-os",
                "version": "1.0.0",
                "environment": config.ENV,
            }

    def _setup_domain_routes(self, app: FastAPI) -> None:
        """Configure domain routers

        Args:
            app: FastAPI application to configure
        """
        for router, prefix in self._domain_routers:
            app.include_router(router, prefix=prefix)

    def _setup_startup_event(
        self,
        app: FastAPI,
        agent_cache: Any,
        agent_provider: Any,
    ) -> None:
        """Configure startup event handler

        Args:
            app: FastAPI application to configure
            agent_cache: Agent cache service
            agent_provider: Agent provider service
        """

        @app.on_event("startup")
        async def initialize_on_startup() -> None:
            # Initialize database
            await initialize_database()

            # Start FastStream for events
            await faststream_app.start()
            logger.info("🚀 FastStream started")

            # Load agents and setup runtime
            _, runtime_agents = await agent_cache.load_all_agents()
            nonlocal app
            app = agent_provider.setup_runtime_with_app(runtime_agents, app)

    def _setup_shutdown_event(self, app: FastAPI) -> None:
        """Configure shutdown event handler

        Args:
            app: FastAPI application to configure
        """

        @app.on_event("shutdown")
        async def cleanup_on_shutdown() -> None:
            await faststream_app.stop()
            logger.info("🛑 FastStream stopped")
