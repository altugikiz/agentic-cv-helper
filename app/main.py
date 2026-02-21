"""FastAPI application entry point for the Career Assistant AI Agent."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, setup_logging
from app.routers.message_router import router as message_router

# Initialise logging early
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    application = FastAPI(
        title="Career Assistant AI Agent",
        description=(
            "Multi-agent system that evaluates employer messages, generates "
            "professional responses, and ensures quality via an LLM-as-Judge "
            "evaluator before delivery."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow all origins during development
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    application.include_router(message_router)

    @application.on_event("startup")
    async def _startup() -> None:
        logger.info(
            "Career Assistant starting — model=%s threshold=%.2f max_iter=%d",
            settings.openai_model,
            settings.evaluator_threshold,
            settings.max_revision_iterations,
        )

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
