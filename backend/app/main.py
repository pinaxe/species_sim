"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.router import router as api_v1_router
from .core.config import settings
from .core.logging import setup_logging, get_logger
from .core.redis import get_redis, close_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    # Startup
    setup_logging()
    logger.info("Starting BioSim-Engine", version=settings.api_version)
    redis = await get_redis()
    logger.info("Redis connected")
    yield

    # Shutdown
    await close_redis()
    logger.info("Shutting down BioSim-Engine")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_v1_router)

    @app.get("/")
    async def root():
        """API root endpoint."""
        return {
            "title": settings.api_title,
            "version": settings.api_version,
            "docs": "/docs",
        }

    return app


# Create app instance for uvicorn
app = create_app()
