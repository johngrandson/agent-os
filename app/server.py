import logging

from app.agents.api.routers import agent_router
from app.container import Container
from app.events import setup_broker_with_handlers
from app.initialization import initialize_database, setup_agent_os_with_app
from app.webhook.api.routers import webhook_router
from core.config import config
from core.exceptions import CustomException
from core.fastapi.dependencies import Logging
from core.fastapi.middlewares import ResponseLogMiddleware, SQLAlchemyMiddleware
from core.logging_config import configure_logging
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# Load environment variables
load_dotenv()

# Configure logging early
configure_logging(debug=config.DEBUG)
logger = logging.getLogger(__name__)


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
        return {"status": "healthy", "service": "agent-os"}

    app.include_router(agent_router, prefix="/api/v1/agents")
    app.include_router(webhook_router, prefix="/api/v1")


def setup_dependency_injection(container: Container):
    """Configure dependency injection"""
    container.wire(
        modules=[
            "app.agents.api.routers",
            "app.webhook.api.routers",
        ]
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    # Create container and setup DI
    container = Container()
    setup_dependency_injection(container)

    # Setup event broker with all registered handlers
    setup_broker_with_handlers()

    # Get shared agent loader from container
    agent_loader = container.agent_loader()
    webhook_processor = container.webhook_agent_processor()

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

        # Load agents for both AgentOS and webhook processing
        await agent_loader.load_all_active_agents()
        await webhook_processor.initialize_agents()

        # Setup AgentOS with loaded agents
        nonlocal app
        app = setup_agent_os_with_app(agent_loader.agno_agents, app)

    return app


# App should be created by the ASGI server or startup script
