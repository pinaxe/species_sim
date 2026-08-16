"""
data.py
=======

Environment providers for the simulator.

Three ways to get an :class:`model.Environment`:

1. :func:`synthetic_environment` -- a physically-motivated but *procedural*
   climate (latitudinal temperature gradient + orographic noise + an ITCZ /
   subtropical-desert / mid-latitude precipitation profile). Zero downloads,
   deterministic, runs anywhere. This is the default so the app works the
   moment you clone it.

2. :func:`geotiff_environment` -- real bioclimatic rasters (WorldClim
   ``bio1``/``bio12``, CHELSA, TerraClimate, ...) read with ``rasterio``,
   reprojected/windowed onto the requested bounding box.

3. :func:`gbif_occurrences` -- optional GBIF occurrence points for the
   species you are simulating, useful both as a visual sanity check and as
   input to :func:`fit_niche_from_occurrences`, which estimates the thermal
   and hydric optima directly from where the species actually lives.

Every heavy import (``rasterio``, ``geopandas``, ``pygbif``) is *lazy* and
guarded, so the app degrades gracefully rather than refusing to start.
"""

from __future__ import annotations

import functools
import math
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from model import Environment, GridSpec, NicheParams

__all__ = [
    "REGIONS",
    "RegionPreset",
    "synthetic_environment",
    "geotiff_environment",
    "load_environment",
    "gbif_occurrences",
    "fit_niche_from_occurrences",
    "sample_layers_at_points",
]

DATA_DIR = os.environ.get("SPECIES_SIM_DATA", os.path.join(os.path.dirname(__file__), "data"))


# --------------------------------------------------------------------------- #
# Region presets
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RegionPreset:
    name: str
    west: float
    south: float
    east: float
    north: float
    #: Suggested grid resolution in degrees for a responsive UI.
    resolution_deg: float = 0.25

    def to_grid(self, resolution_deg: Optional[float] = None) -> GridSpec:
        res = resolution_deg or self.resolution_deg
        n_cols = max(8, int(round((self.east - self.west) / res)))
        n_rows = max(8, int(round((self.north - self.south) / res)))
        return GridSpec(self.west, self.south, self.east, self.north, n_rows, n_cols)

    @property
    def center(self) -> Tuple[float, float]:
        return (0.5 * (self.south + self.north), 0.5 * (self.west + self.east))


REGIONS: Dict[str, RegionPreset] = {
    "Pacific Northwest": RegionPreset("Pacific Northwest", -128.0, 41.0, -114.0, 55.0, 0.10),
    "Contiguous USA": RegionPreset("Contiguous USA", -125.0, 24.0, -66.0, 50.0, 0.25),
    "Europe": RegionPreset("Europe", -11.0, 35.0, 32.0, 62.0, 0.20),
    "Australia": RegionPreset("Australia", 112.0, -44.0, 154.0, -10.0, 0.25),
    "Southern Africa": RegionPreset("Southern Africa", 11.0, -35.0, 41.0, -15.0, 0.20),
    "Southeast Asia": RegionPreset("Southeast Asia", 92.0, -11.0, 141.0, 24.0, 0.25),
    "New Zealand": RegionPreset("New Zealand", 166.0, -47.5, 179.0, -34.0, 0.08),
    "Global": RegionPreset("Global", -180.0, -60.0, 180.0, 75.0, 1.0),
}


# --------------------------------------------------------------------------- #
# Procedural terrain / climate
# --------------------------------------------------------------------------- #
def _value_noise(shape: Tuple[int, int], octaves: int, rng: np.random.Generator) -> np.ndarray:
    """Cheap fractal (pink-ish) noise in [0, 1] via summed bilinear upsamples."""
    from scipy.ndimage import zoom

    n_rows, n_cols = shape
    out = np.zeros(shape, dtype=np.float32)
    amplitude, total = 1.0, 0.0
    for o in range(octaves):
        res = 2 ** (o + 1)
        coarse = rng.random((max(2, min(res, n_rows)), max(2, min(res, n_cols))))
        zy = n_rows / coarse.shape[0]
        zx = n_cols / coarse.shape[1]
        layer = zoom(coarse, (zy, zx), order=3)[:n_rows, :n_cols]
        if layer.shape != shape:  # zoom rounding
            pad_y = shape[0] - layer.shape[0]
            pad_x = shape[1] - layer.shape[1]
            layer = np.pad(layer, ((0, max(0, pad_y)), (0, max(0, pad_x))), mode="edge")
            layer = layer[: shape[0], : shape[1]]
        out += amplitude * layer.astype(np.float32)
        total += amplitude
        amplitude *= 0.5
    out /= total
    out -= out.min()
    denom = out.max() or 1.0
    return out / denom


def _latitudinal_temperature(lat2d: np.ndarray) -> np.ndarray:
    """Zonal mean annual temperature, a smooth fit to the observed profile."""
    lat = np.abs(lat2d)
    return 28.0 - 0.0068 * lat**2 - 0.055 * lat


def _latitudinal_precipitation(lat2d: np.ndarray) -> np.ndarray:
    """ITCZ peak, subtropical dry belts near +/-25 deg, mid-latitude storm track."""
    lat = lat2d
    itcz = 2400.0 * np.exp(-0.5 * (lat / 9.0) ** 2)
    storm_n = 900.0 * np.exp(-0.5 * ((lat - 50.0) / 12.0) ** 2)
    storm_s = 900.0 * np.exp(-0.5 * ((lat + 48.0) / 12.0) ** 2)
    base = 220.0
    return itcz + storm_n + storm_s + base


def synthetic_environment(
    grid: GridSpec,
    seed: int = 42,
    land_fraction: float = 0.72,
    relief_km: float = 2.2,
    continentality: float = 3.5,
    name: str = "Synthetic climate",
    all_land: bool = False,
) -> Environment:
    """Generate a plausible temperature/precipitation/land stack for ``grid``.

    The construction is deliberately transparent:

    * **Elevation** -- fractal noise scaled to ``relief_km``; the land/sea
      split is the ``land_fraction`` quantile of that field.
    * **Temperature** -- zonal profile, minus a 6.5 degC/km lapse rate, minus a
      continentality term that cools cells far from the nearest ocean, plus
      fine-scale noise.
    * **Precipitation** -- zonal profile modulated by an orographic term
      (windward uplift) and a rain-shadow term, floored at 30 mm/yr.

    Deterministic for a given ``seed``, so a shared link reproduces exactly.
    """
    rng = np.random.default_rng(seed)
    lon2d, lat2d = grid.mesh
    shape = grid.shape

    relief = _value_noise(shape, octaves=6, rng=rng)
    # Most land is lowland; only the top ~35% of the relief field becomes
    # mountainous, which keeps the mean lapse-rate cooling realistic.
    elevation_km = relief_km * np.clip(relief - 0.65, 0.0, None) / 0.35

    if all_land:
        land = np.ones(shape, dtype=bool)
    else:
        threshold = np.quantile(relief, 1.0 - land_fraction)
        land = relief > threshold

    # Distance to the nearest ocean cell drives continentality.
    if land.all():
        dist_to_sea = np.zeros(shape, dtype=np.float32)
    else:
        from scipy.ndimage import distance_transform_edt

        dist_cells = distance_transform_edt(land)
        dist_to_sea = (dist_cells * grid.cell_width_km / 500.0).astype(np.float32)

    temperature = (
        _latitudinal_temperature(lat2d)
        - 6.5 * elevation_km
        - continentality * np.tanh(dist_to_sea)
        + 2.5 * (_value_noise(shape, 4, rng) - 0.5)
    )

    orography = np.gradient(elevation_km, axis=1)  # west-east uplift proxy
    precipitation = (
        _latitudinal_precipitation(lat2d)
        * (1.0 + 1.6 * np.clip(orography, 0, None) - 0.9 * np.clip(-orography, 0, None))
        * (0.6 + 0.8 * _value_noise(shape, 5, rng))
    )
    precipitation = np.clip(precipitation, 30.0, 6000.0)

    return Environment(
        grid=grid,
        temperature=temperature.astype(np.float32),
        precipitation=precipitation.astype(np.float32),
        land_mask=land,
        name=name,
    )


# --------------------------------------------------------------------------- #
# Real rasters
# --------------------------------------------------------------------------- #
def _read_window(path: str, grid: GridSpec) -> np.ndarray:
    """Read ``path`` and resample it onto ``grid`` (nearest, WGS84 assumed)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
    from rasterio.transform import from_bounds

    dst_transform = from_bounds(
        grid.west, grid.south, grid.east, grid.north, grid.n_cols, grid.n_rows
    )
    destination = np.full(grid.shape, np.nan, dtype=np.float32)

    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs or "EPSG:4326",
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
        )
    return destination


def geotiff_environment(
    grid: GridSpec,
    temperature_path: str,
    precipitation_path: Optional[str] = None,
    temperature_scale: float = 1.0,
    temperature_offset: float = 0.0,
    name: str = "GeoTIFF climate",
) -> Environment:
    """Build an :class:`Environment` from real GeoTIFF climate layers.

    Notes
    -----
    * WorldClim v2 ``bio1`` (mean annual temperature) is already in degC;
      WorldClim v1 stores degC * 10, so pass ``temperature_scale=0.1``.
    * ``bio12`` is annual precipitation in mm -- no scaling needed.
    * Cells that are nodata in the temperature raster become ocean
      (``land_mask=False``), which is exactly what WorldClim's ocean fill
      gives you for free.

    Raises
    ------
    ImportError
        If ``rasterio`` is not installed.
    """
    temperature = _read_window(temperature_path, grid) * temperature_scale + temperature_offset
    land = np.isfinite(temperature)

    if precipitation_path:
        precipitation = _read_window(precipitation_path, grid)
        land &= np.isfinite(precipitation)
    else:
        _, lat2d = grid.mesh
        precipitation = _latitudinal_precipitation(lat2d).astype(np.float32)

    temperature = np.nan_to_num(temperature, nan=-99.0)
    precipitation = np.nan_to_num(precipitation, nan=0.0)

    return Environment(
        grid=grid,
        temperature=temperature,
        precipitation=precipitation,
        land_mask=land,
        name=name,
    )


def discover_rasters(directory: str = DATA_DIR) -> Dict[str, str]:
    """Return ``{filename: path}`` for GeoTIFFs sitting in the data folder."""
    if not os.path.isdir(directory):
        return {}
    return {
        f: os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.lower().endswith((".tif", ".tiff"))
    }


def load_environment(
    region: str = "Pacific Northwest",
    resolution_deg: Optional[float] = None,
    temperature_path: Optional[str] = None,
    precipitation_path: Optional[str] = None,
    temperature_scale: float = 1.0,
    seed: int = 42,
) -> Environment:
    """One-call entry point: real rasters when supplied, synthetic otherwise."""
    preset = REGIONS.get(region, REGIONS["Pacific Northwest"])
    grid = preset.to_grid(resolution_deg)

    if temperature_path and os.path.exists(temperature_path):
        try:
            return geotiff_environment(
                grid,
                temperature_path,
                precipitation_path if precipitation_path and os.path.exists(precipitation_path) else None,
                temperature_scale=temperature_scale,
                name=f"{preset.name} (GeoTIFF)",
            )
        except ImportError:
            pass  # rasterio missing -> fall through to synthetic

    return synthetic_environment(grid, seed=seed, name=f"{preset.name} (synthetic)")


# --------------------------------------------------------------------------- #
# GBIF occurrences
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=32)
def gbif_occurrences(
    scientific_name: str,
    west: float,
    south: float,
    east: float,
    north: float,
    limit: int = 500,
) -> Tuple[Tuple[float, float], ...]:
    """Fetch georeferenced GBIF occurrences as ``((lon, lat), ...)``.

    Returns an empty tuple if ``pygbif`` is unavailable or the request fails --
    occurrence points are a nice-to-have overlay, never a hard dependency.
    Results are cached per (name, bbox) so slider moves do not re-query.
    """
    try:
        from pygbif import occurrences as gbif_occ
    except Exception:
        return ()

    wkt = (
        f"POLYGON(({west} {south}, {east} {south}, "
        f"{east} {north}, {west} {north}, {west} {south}))"
    )
    points: List[Tuple[float, float]] = []
    try:
        offset = 0
        while len(points) < limit:
            resp = gbif_occ.search(
                scientificName=scientific_name,
                geometry=wkt,
                hasCoordinate=True,
                hasGeospatialIssue=False,
                limit=min(300, limit - len(points)),
                offset=offset,
            )
            results = resp.get("results", [])
            if not results:
                break
            for rec in results:
                lon, lat = rec.get("decimalLongitude"), rec.get("decimalLatitude")
                if lon is not None and lat is not None:
                    points.append((float(lon), float(lat)))
            if resp.get("endOfRecords", True):
                break
            offset += len(results)
    except Exception:
        return tuple(points)
    return tuple(points)


def sample_layers_at_points(
    env: Environment, points: Iterable[Tuple[float, float]]
) -> Dict[str, np.ndarray]:
    """Sample every environmental layer at ``(lon, lat)`` points."""
    rows, cols = [], []
    for lon, lat in points:
        rc = env.grid.lonlat_to_rc(lon, lat)
        if rc is not None:
            rows.append(rc[0])
            cols.append(rc[1])
    if not rows:
        return {k: np.array([]) for k in env.layers}
    r = np.asarray(rows)
    c = np.asarray(cols)
    valid = env.land_mask[r, c]
    return {k: v[r, c][valid] for k, v in env.layers.items()}


def fit_niche_from_occurrences(
    env: Environment,
    points: Iterable[Tuple[float, float]],
    base: Optional[NicheParams] = None,
    tolerance_quantile: float = 0.9,
) -> Optional[NicheParams]:
    """Estimate a Gaussian niche from realised occurrences.

    Uses the median as the optimum (robust to sampling bias toward roads and
    cities) and a quantile-based spread as sigma, which is far less sensitive
    to a handful of misidentified outliers than the raw standard deviation.
    Returns ``None`` if fewer than 10 usable points fall inside the grid.
    """
    samples = sample_layers_at_points(env, points)
    temps = samples.get("temperature", np.array([]))
    precs = samples.get("precipitation", np.array([]))
    if temps.size < 10:
        return None

    def _spread(a: np.ndarray) -> float:
        lo, hi = np.quantile(a, [1 - tolerance_quantile, tolerance_quantile])
        # Convert an inter-quantile range into a Gaussian sigma.
        z = 2.0 * abs(float(np.sqrt(2)) * 1.2816)  # ~90% interval width in sigmas
        return max(float(hi - lo) / z, 1e-3)

    b = base or NicheParams()
    return NicheParams(
        t_opt=float(np.median(temps)),
        t_tol=_spread(temps),
        p_opt=float(np.median(precs)) if precs.size else b.p_opt,
        p_tol=_spread(precs) if precs.size else b.p_tol,
        use_precipitation=b.use_precipitation,
        suitability_floor=b.suitability_floor,
    )
