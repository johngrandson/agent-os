from fastapi import FastAPI, Depends, Request
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
import logging

from app.container import ApplicationContainer
from core.logging_config import configure_logging
from core.config import config
from app.agents.api.routers import agent_router
from app.knowledge.api.routers import knowledge_router

# Enhanced knowledge now integrated into main knowledge router
from app.tools.api.routers import router as tool_router
from app.tasks.api.routers import router as task_router
from app.events.api.routers import router as event_router
from app.events.api.websocket_router import router as websocket_router
from app.integrations.api.routers import router as integration_router
from app.teams.api.routers import router as team_router
from app.workflows.api.routers import router as workflow_router
from app.startup import StartupManager

from core.exceptions import CustomException
from core.fastapi.middlewares import SQLAlchemyMiddleware, ResponseLogMiddleware
from core.fastapi.dependencies import Logging

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
        return {"status": "healthy", "service": "agent-os"}

    app.include_router(agent_router, prefix="/api/v1/agents")
    app.include_router(knowledge_router, prefix="/api/v1/knowledge")
    app.include_router(tool_router, prefix="/api/v1")
    app.include_router(task_router, prefix="/api/v1")
    app.include_router(event_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")
    app.include_router(integration_router, prefix="/api/v1")
    app.include_router(team_router, prefix="/api/v1")
    app.include_router(workflow_router, prefix="/api/v1")


def setup_dependency_injection(container: ApplicationContainer):
    """Configure dependency injection"""
    container.wire(
        modules=[
            "app.agents.api.routers",
            "app.knowledge.api.routers",
            "app.tools.api.routers",
            "app.tasks.api.routers",
            "app.integrations.api.routers",
            "app.teams.api.routers",
            "app.workflows.api.routers",
        ]
    )
    agent_router.container = container
    knowledge_router.container = container
    tool_router.container = container
    task_router.container = container
    integration_router.container = container
    team_router.container = container
    workflow_router.container = container


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    # Create container and setup DI
    container = ApplicationContainer()
    setup_dependency_injection(container)

    # Create startup manager
    startup_manager = StartupManager()

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
        await startup_manager.initialize_database()
        await startup_manager.initialize_tools()
        await startup_manager.initialize_event_system()

        # Setup AgentOS after agents are loaded
        nonlocal app
        app = startup_manager.setup_agent_os_sync(app)

    return app


app = create_app()
