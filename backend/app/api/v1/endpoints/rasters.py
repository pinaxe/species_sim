"""Raster data endpoints for climate and environmental layers."""

from fastapi import APIRouter, HTTPException, Query

from app.models.raster import RasterBBoxResponse, RasterClipRequest, RasterClipResponse
from app.services.climate_service import ClimateService

router = APIRouter(prefix="/rasters", tags=["Rasters"])
climate_service = ClimateService()


@router.get("/layers")
async def list_layers() -> dict:
    """List all available climate/environmental layers."""
    try:
        layers = climate_service.list_available_layers()
        return {
            "count": len(layers),
            "layers": [layer.model_dump() for layer in layers],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clip")
async def clip_raster(request: RasterClipRequest) -> RasterClipResponse:
    """Clip a raster layer to a bounding box."""
    try:
        data = climate_service.clip_raster(
            request.layer_name,
            request.bbox,
            request.resolution_deg,
        )

        # Get metadata
        layers = climate_service.list_available_layers()
        metadata = next(
            (l for l in layers if l.name == request.layer_name),
            None,
        )

        if not metadata:
            raise ValueError(f"Layer not found: {request.layer_name}")

        rows, cols = data.get("data", [[0]]).shape if isinstance(data.get("data"), list) else (0, 0)

        return RasterClipResponse(
            metadata=metadata,
            bbox=request.bbox,
            grid_shape=(rows, cols),
            data=data.get("data", []).tolist() if hasattr(data.get("data"), "tolist") else data.get("data", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bounds")
async def get_raster_bounds(
    bbox: str = Query(..., description="Bounding box as 'west,south,east,north'"),
) -> RasterBBoxResponse:
    """Get available rasters and their extents within a bounding box."""
    try:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must be 'west,south,east,north'")

        layers = climate_service.list_available_layers()
        extents = {
            layer.name: [
                -180 + i * 0.25 for i in range(4)  # Simplified placeholder
            ]
            for layer in layers
        }

        return RasterBBoxResponse(
            available_layers=layers,
            extents=extents,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
