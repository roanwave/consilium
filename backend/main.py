"""Consilium FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import router as api_router
from backend.config import get_settings
from backend.lib.exceptions import (
    ConsiliumError,
    LLMError,
    SessionExpiredError,
    SessionNotFoundError,
    ValidationError,
)
from backend.lib.llm import close_llm_client, get_llm_client
from backend.lib.models import (
    CommanderCompetence,
    ConfigResponse,
    Era,
    HealthResponse,
    NarrativeOutcome,
    TerrainType,
    ViolenceLevel,
)
from backend.lib.persistence import close_session_store, get_session_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    settings = get_settings()

    # Startup
    logger.info("Starting Consilium...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Session directory: {settings.session_dir}")

    # Initialize session store
    store = await get_session_store()
    logger.info(f"Session store initialized: {store.get_cache_stats()}")

    # Initialize LLM client
    if settings.has_anthropic_key or settings.has_openrouter_key:
        await get_llm_client()
        logger.info("LLM client initialized")
    else:
        logger.warning("No API keys configured - LLM calls will fail")

    yield

    # Shutdown
    logger.info("Shutting down Consilium...")
    await close_session_store()
    await close_llm_client()
    logger.info("Shutdown complete")


# =============================================================================
# Application Factory
# =============================================================================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Consilium",
        description="Multi-agent medieval battle wargaming engine",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    register_exception_handlers(app)

    # Routes
    app.include_router(api_router, prefix="/api")

    # Root endpoints
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(status="ok", version="0.1.0")

    @app.get("/api/config", response_model=ConfigResponse, tags=["Config"])
    async def get_config() -> ConfigResponse:
        """Get available configuration options."""
        return ConfigResponse(
            eras=[{"value": e.value, "label": e.value.replace("_", " ").title()} for e in Era],
            terrain_types=[
                {"value": t.value, "label": t.value.replace("_", " ").title()}
                for t in TerrainType
            ],
            violence_levels=[
                {"value": v.value, "label": v.value.title()} for v in ViolenceLevel
            ],
            commander_competence=[
                {"value": c.value, "label": c.value.title()} for c in CommanderCompetence
            ],
            narrative_outcomes=[
                {"value": n.value, "label": n.value.replace("_", " ").title()}
                for n in NarrativeOutcome
            ],
        )

    return app


# =============================================================================
# Exception Handlers
# =============================================================================


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(SessionNotFoundError)
    async def session_not_found_handler(
        request: Request, exc: SessionNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message, "session_id": exc.session_id},
        )

    @app.exception_handler(SessionExpiredError)
    async def session_expired_handler(
        request: Request, exc: SessionExpiredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=410,
            content={"detail": exc.message, "session_id": exc.session_id},
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.message,
                "field": exc.field,
                "value": str(exc.value) if exc.value else None,
            },
        )

    @app.exception_handler(LLMError)
    async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
        logger.error(f"LLM error: {exc.message}")
        return JSONResponse(
            status_code=503,
            content={"detail": "LLM service error", "error": exc.message},
        )

    @app.exception_handler(ConsiliumError)
    async def consilium_error_handler(
        request: Request, exc: ConsiliumError
    ) -> JSONResponse:
        logger.error(f"Consilium error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message, "details": exc.details},
        )


# =============================================================================
# Application Instance
# =============================================================================


app = create_app()
