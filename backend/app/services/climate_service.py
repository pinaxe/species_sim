"""Climate and environmental data service using rasterio."""

from pathlib import Path
from typing import Optional

import numpy as np
from rasterio.io import MemoryFile

from ..core.config import settings
from ..core.logging import get_logger
from ..models.raster import RasterMetadata

logger = get_logger(__name__)

# Procedural climate fallback
try:
    import rasterio
    from rasterio.mask import mask
except ImportError:
    rasterio = None


class ClimateService:
    """Manage climate layers and environmental data."""

    def __init__(self):
        self.cache_dir = Path(settings.climate_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._procedural_cache: dict = {}

    def get_procedural_climate(
        self,
        bbox: tuple[float, float, float, float],
        resolution_deg: float = 0.25,
    ) -> dict[str, np.ndarray]:
        """Generate procedural climate layers (fallback when no real data)."""
        west, south, east, north = bbox
        rows = int((north - south) / resolution_deg)
        cols = int((east - west) / resolution_deg)

        # Create synthetic gradients
        lats = np.linspace(south, north, rows)
        lons = np.linspace(west, east, cols)
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        # Temperature: tropical at equator, cold at poles
        temperature = 25.0 - (lat_grid ** 2) / 50.0 + np.random.normal(0, 2, (rows, cols))

        # Precipitation: more at equator and coasts
        distance_to_coast = np.abs(lat_grid - 30) + np.abs(lon_grid - 0)
        precipitation = (
            1000 * np.exp(-distance_to_coast / 20)
            + np.random.normal(200, 50, (rows, cols))
        )
        precipitation = np.clip(precipitation, 100, 3000)

        return {
            "temperature": temperature,
            "precipitation": precipitation,
            "lats": lats,
            "lons": lons,
        }

    def climate_at_points(
        self, lons: np.ndarray, lats: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate the *deterministic* part of the procedural climate model at
        arbitrary (lon, lat) points -- no grid, no per-cell noise.

        This is the same formula :meth:`get_procedural_climate` grids up for a
        simulation run, minus the random jitter: niche-fitting wants the
        central climate a species actually experiences at its real occurrence
        coordinates, not one noisy draw of the grid. Keeping the formula
        identical (mean of the noise terms folded in as a constant) means a
        niche fitted here lines up with whatever a later simulation run
        generates for the same region.
        """
        lons = np.asarray(lons, dtype=np.float64)
        lats = np.asarray(lats, dtype=np.float64)

        temperature = 25.0 - (lats ** 2) / 50.0

        distance_to_coast = np.abs(lats - 30) + np.abs(lons - 0)
        precipitation = 1000 * np.exp(-distance_to_coast / 20) + 200.0  # +200 = noise mean
        precipitation = np.clip(precipitation, 100, 3000)

        return temperature, precipitation

    def clip_raster(
        self,
        layer_name: str,
        bbox: tuple[float, float, float, float],
        resolution_deg: Optional[float] = None,
    ) -> dict:
        """Clip a raster layer to a bounding box."""
        if not rasterio:
            logger.warning("rasterio not available, using procedural climate")
            return self.get_procedural_climate(bbox, resolution_deg or 0.25)

        # Try to load from GeoTIFF
        raster_path = self.cache_dir / f"{layer_name}.tif"
        if not raster_path.exists():
            logger.warning(f"Raster not found: {raster_path}, using procedural")
            return self.get_procedural_climate(bbox, resolution_deg or 0.25)

        try:
            with rasterio.open(raster_path) as src:
                window = src.window(*bbox)
                data = src.read(1, window=window)
                transform = src.window_transform(window)
                crs = src.crs

                logger.info(f"Clipped {layer_name}", shape=data.shape, bbox=bbox)
                return {
                    "data": data,
                    "transform": transform,
                    "crs": crs,
                }
        except Exception as e:
            logger.error(f"Error clipping raster: {e}")
            return self.get_procedural_climate(bbox, resolution_deg or 0.25)

    def list_available_layers(self) -> list[RasterMetadata]:
        """List all available climate layers."""
        if not rasterio:
            return self._get_procedural_metadata()

        layers = []
        for tif_file in self.cache_dir.glob("*.tif"):
            try:
                with rasterio.open(tif_file) as src:
                    data = src.read(1)
                    layers.append(
                        RasterMetadata(
                            name=tif_file.stem,
                            variable=tif_file.stem.split("_")[-1],
                            unit="varies",
                            min_value=float(np.nanmin(data)),
                            max_value=float(np.nanmax(data)),
                            mean_value=float(np.nanmean(data)),
                            crs=str(src.crs),
                            resolution_deg=abs(src.res[0]),
                        )
                    )
            except Exception as e:
                logger.warning(f"Error reading {tif_file}: {e}")

        return layers if layers else self._get_procedural_metadata()

    @staticmethod
    def _get_procedural_metadata() -> list[RasterMetadata]:
        """Get metadata for procedural climate layers."""
        return [
            RasterMetadata(
                name="temperature",
                variable="temperature",
                unit="°C",
                min_value=-20.0,
                max_value=40.0,
                mean_value=15.0,
                resolution_deg=0.25,
            ),
            RasterMetadata(
                name="precipitation",
                variable="precipitation",
                unit="mm",
                min_value=100.0,
                max_value=3000.0,
                mean_value=1000.0,
                resolution_deg=0.25,
            ),
        ]
