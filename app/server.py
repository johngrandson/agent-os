from app.agents.api.routers import agent_router
from app.container import Container
from app.events import faststream_app, setup_broker_with_handlers
from app.initialization import initialize_database
from app.webhooks.api.routers import webhook_router
from core.config import config
from core.exceptions import CustomException
from core.fastapi.dependencies import Logging
from core.fastapi.middlewares import ResponseLogMiddleware, SQLAlchemyMiddleware
from core.logger import get_module_logger
from core.logging_config import configure_logging
from dotenv import load_dotenv
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastapi import Depends, FastAPI, Request


# Load environment variables
load_dotenv()

# Configure logging early
configure_logging(debug=config.DEBUG)
logger = get_module_logger(__name__)


def create_middlewares():
    """Configure application middlewares"""
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


def setup_exception_handlers(app: FastAPI):
    """Configure application exception handlers"""

    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.code,
            content={"error_code": exc.error_code, "message": exc.message},
        )


def setup_routes(app: FastAPI):
    """Configure application routes"""

    @app.get("/api/v1/health")
    async def health_check():
        """Basic health check endpoint"""
        return {
            "status": "healthy",
            "service": "agent-os",
            "version": "1.0.0",
            "environment": config.ENV,
        }

    app.include_router(agent_router, prefix="/api/v1/agents")
    app.include_router(webhook_router, prefix="/api/v1/webhook")


def setup_dependency_injection(container: Container):
    """Configure dependency injection"""
    container.wire(
        modules=[
            "app.agents.api.routers",
            "app.webhooks.api.routers",
        ]
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    # Create container and setup DI
    container = Container()
    setup_dependency_injection(container)

    # Setup event broker with all registered handlers
    setup_broker_with_handlers()

    # Get agent cache and provider from container
    agent_cache = container.agent_cache()
    agent_provider = container.agent_provider()

    # Create FastAPI app
    app = FastAPI(
        title="Agent OS API",
        description="Agent Operating System with integrated AgentOS support",
        version="1.0.0",
        dependencies=[Depends(Logging)],
        middleware=create_middlewares(),
    )

    # Setup app components
    setup_exception_handlers(app)
    setup_routes(app)

    # Setup startup event
    @app.on_event("startup")
    async def initialize_on_startup():
        # Initialize database (simple function call)
        await initialize_database()

        # Start the FastStream application for both publishing and consuming
        try:
            await faststream_app.start()
            logger.info("🚀 EVENTS: FastStream started - Publishers & Handlers active")
        except Exception as e:
            logger.error(f"❌ EVENTS: FastStream failed - {e}")
            # Don't raise here to allow app to start, but log the issue
            # This ensures the API is still functional even if events fail

        # Load all agents once
        db_agents, _ = await agent_cache.load_all_agents()

        # Convert agents for runtime using provider
        runtime_agents = await agent_provider.convert_agents_for_runtime(db_agents)

        # Setup runtime system (AgentOS) with provider
        nonlocal app
        app = agent_provider.setup_runtime_with_app(runtime_agents, app)

    # Setup shutdown event
    @app.on_event("shutdown")
    async def cleanup_on_shutdown():
        # Stop the FastStream application
        try:
            await faststream_app.stop()
            logger.info("🛑 EVENTS: FastStream stopped")
        except Exception as e:
            logger.error(f"❌ EVENTS: Stop failed - {e}")

    return app


# App should be created by the ASGI server or startup script
