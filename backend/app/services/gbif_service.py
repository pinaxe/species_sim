"""GBIF API integration and spatial thinning."""

import math
from typing import Optional

import httpx
import numpy as np
import pandas as pd

from ..core.config import settings
from ..core.logging import get_logger
from ..models.gbif import Occurrence, OccurrenceSearchResponse

logger = get_logger(__name__)


class GBIFService:
    """Client for GBIF API with spatial thinning."""

    def __init__(self):
        self.api_url = settings.gbif_api_url
        self.timeout = settings.gbif_timeout

    async def search_taxa(self, query: str, limit: int = 10) -> list[dict]:
        """Search for taxa by scientific name."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.api_url}/species/search",
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            # Transform GBIF response to match Taxon model
            transformed = []
            for r in results:
                transformed.append({
                    "key": r.get("key"),
                    "name": r.get("scientificName", r.get("canonicalName", "Unknown")),
                    "canonicalName": r.get("canonicalName"),
                    "rank": r.get("rank"),
                })
            return transformed

    async def search_occurrences(
        self,
        taxon_key: int,
        limit: int = 10000,
        geometry: Optional[str] = None,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
    ) -> OccurrenceSearchResponse:
        """Fetch occurrences for a taxon with optional spatial/temporal filters."""
        params = {
            "taxonKey": taxon_key,
            "limit": min(limit, 300000),
            "offset": 0,
            "hasCoordinate": True,
        }

        if geometry:
            params["geometry"] = geometry
        if year_start:
            params["year"] = f"{year_start},{year_end or 2025}"

        occurrences = []
        offset = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while offset < limit:
                params["offset"] = offset
                logger.info("Fetching GBIF occurrences", taxon_key=taxon_key, offset=offset)

                resp = await client.get(
                    f"{self.api_url}/occurrence/search",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if not results:
                    break

                for rec in results:
                    if len(occurrences) >= limit:
                        break
                    occ = Occurrence(
                        key=rec.get("key"),
                        datasetKey=rec.get("datasetKey"),
                        scientificName=rec.get("scientificName"),
                        decimalLatitude=rec.get("decimalLatitude"),
                        decimalLongitude=rec.get("decimalLongitude"),
                        year=rec.get("year"),
                        month=rec.get("month"),
                        day=rec.get("day"),
                        coordinateUncertaintyInMeters=rec.get("coordinateUncertaintyInMeters"),
                    )
                    occurrences.append(occ)

                offset = data.get("offset", 0) + data.get("limit", 0)
                if not data.get("endOfRecords", True):
                    break

        taxon_name = data.get("results", [{}])[0].get("scientificName", "Unknown")

        return OccurrenceSearchResponse(
            count=len(occurrences),
            total=data.get("count", 0),
            limit=limit,
            offset=0,
            results=occurrences,
            taxon_name=taxon_name,
        )

    def spatial_thin(
        self,
        occurrences: list[Occurrence],
        grid_size_km: float = 10.0,
    ) -> list[Occurrence]:
        """Thin occurrences to one per grid cell (spatial thinning)."""
        if not occurrences:
            return []

        df = pd.DataFrame([
            {
                "key": o.key,
                "lon": o.decimalLongitude,
                "lat": o.decimalLatitude,
            }
            for o in occurrences
        ])

        # Convert km to degrees (approximate)
        deg_per_km = 1.0 / 111.0
        grid_deg = grid_size_km * deg_per_km

        df["grid_x"] = (df["lon"] / grid_deg).astype(int)
        df["grid_y"] = (df["lat"] / grid_deg).astype(int)

        # Keep first occurrence per grid cell
        thinned = df.drop_duplicates(subset=["grid_x", "grid_y"], keep="first")

        thinned_keys = set(thinned["key"].values)
        return [o for o in occurrences if o.key in thinned_keys]

    def fit_niche(self, occurrences: list[Occurrence], env_data: dict) -> dict:
        """Fit Gaussian niche envelope from occurrence points."""
        if not occurrences:
            return {}

        lats = np.array([o.decimalLatitude for o in occurrences])
        lons = np.array([o.decimalLongitude for o in occurrences])

        # Extract environmental values at occurrence locations
        temp_vals = []
        precip_vals = []

        for lat, lon in zip(lats, lons):
            t = self._interp_env(lon, lat, env_data.get("temperature", []))
            p = self._interp_env(lon, lat, env_data.get("precipitation", []))
            if t is not None and p is not None:
                temp_vals.append(t)
                precip_vals.append(p)

        if not temp_vals or not precip_vals:
            return {}

        temp_vals = np.array(temp_vals)
        precip_vals = np.array(precip_vals)

        return {
            "temperature_opt": float(np.median(temp_vals)),
            "temperature_sigma": float(np.percentile(temp_vals, 75) - np.percentile(temp_vals, 25)),
            "precipitation_opt": float(np.median(precip_vals)),
            "precipitation_sigma": float(np.percentile(precip_vals, 75) - np.percentile(precip_vals, 25)),
        }

    @staticmethod
    def _interp_env(lon: float, lat: float, grid: list[list[float]]) -> Optional[float]:
        """Simple bilinear interpolation on a lat/lon grid."""
        if not grid or not grid[0]:
            return None
        return np.mean(grid)  # Placeholder
