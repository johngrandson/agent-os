"""FastAPI server entry point for Agent OS."""

from app.domains.agent_management.api.routers import agent_router
from app.domains.communication.webhooks.api.routers import webhook_router
from app.domains.evaluation.api.routers import accuracy_eval_router, eval_feedback_router
from app.shared.server.builder import FastAPIServerBuilder

from fastapi import FastAPI


# Build FastAPI app using builder pattern
app = (
    FastAPIServerBuilder()
    .add_domain_router(agent_router, "/api/v1/agents")
    .add_domain_router(webhook_router, "/api/v1/webhook")
    .add_domain_router(eval_feedback_router, "/api/v1/eval-feedback")
    .add_domain_router(accuracy_eval_router, "/api/v1/accuracy-eval")
    .build()
)


def create_app() -> FastAPI:
    """Create and return the FastAPI application instance"""
    return app
