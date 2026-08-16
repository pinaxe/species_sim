"""API router combining all endpoint modules."""

from fastapi import APIRouter

from .endpoints import gbif, rasters, simulation

router = APIRouter(prefix="/api/v1")

router.include_router(gbif.router)
router.include_router(rasters.router)
router.include_router(simulation.router)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
