"""Pydantic models for raster data."""

from typing import Optional

from pydantic import BaseModel, Field


class RasterMetadata(BaseModel):
    """Metadata for a raster layer."""

    name: str = Field(..., description="Layer name (e.g., 'temperature')")
    variable: str = Field(..., description="Variable type")
    unit: str = Field(..., description="Unit (°C, mm, m, etc.)")
    min_value: float
    max_value: float
    mean_value: float
    crs: str = Field("EPSG:4326", description="Coordinate reference system")
    resolution_deg: float = Field(..., description="Resolution in degrees")


class RasterClipRequest(BaseModel):
    """Request to clip a raster to a bounding box."""

    layer_name: str = Field(..., description="Name of layer to clip")
    bbox: tuple[float, float, float, float] = Field(..., description="(west, south, east, north)")
    resolution_deg: Optional[float] = None


class RasterClipResponse(BaseModel):
    """Response from raster clipping."""

    metadata: RasterMetadata
    bbox: tuple[float, float, float, float]
    grid_shape: tuple[int, int]
    data: list[list[float]]  # 2D array


class RasterBBoxResponse(BaseModel):
    """Response listing available rasters."""

    available_layers: list[RasterMetadata]
    extents: dict[str, list[float]]  # layer -> [west, south, east, north]
