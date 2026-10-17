"""GBIF API integration and spatial thinning."""

import math
from typing import Optional

import httpx
import numpy as np
import pandas as pd

from ..core.config import settings
from ..core.logging import get_logger
from ..models.gbif import Occurrence, OccurrenceSearchResponse
from .climate_service import ClimateService

logger = get_logger(__name__)

#: Fewer than this many geolocated occurrences and a niche fit is too noisy
#: to trust -- a handful of points can't tell a wide-ranging generalist from
#: a narrow specialist.
MIN_OCCURRENCES_FOR_NICHE_FIT = 5
#: Converts an inter-quartile range to a Gaussian sigma (IQR ~= 1.349 * sigma
#: for a normal distribution).
_IQR_TO_SIGMA = 1.349


class GBIFService:
    """Client for GBIF API with spatial thinning."""

    def __init__(self):
        self.api_url = settings.gbif_api_url
        self.timeout = settings.gbif_timeout
        self.climate_service = ClimateService()

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
            # Transform GBIF response to match Taxon model.
            #
            # NB: `key` is the hit's id *within whatever checklist dataset
            # matched the search* -- occurrence records are indexed against
            # the GBIF Backbone Taxonomy, so `/occurrence/search?taxonKey=`
            # only returns results for the *backbone* id, `nubKey`. Several
            # checklist entries (e.g. different regional databases) commonly
            # resolve to the same backbone species, so dedupe on it too --
            # otherwise a search returns the same species 2-3x.
            seen_keys: set[int] = set()
            transformed = []
            for r in results:
                taxon_key = r.get("nubKey") or r.get("key")
                if taxon_key is None or taxon_key in seen_keys:
                    continue
                seen_keys.add(taxon_key)
                transformed.append({
                    "key": taxon_key,
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
            "limit": min(limit, 300),  # GBIF's hard per-request page size cap
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
                if data.get("endOfRecords", True):
                    break

        taxon_name = occurrences[0].scientificName if occurrences else "Unknown"

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

    def fit_niche(self, occurrences: list[Occurrence]) -> dict:
        """Fit a Gaussian niche envelope from real GBIF occurrences.

        Evaluates the simulator's own procedural climate formula
        (:meth:`ClimateService.climate_at_points`) directly at each
        occurrence's coordinates -- no raster grid required, and the fitted
        niche lines up with whatever climate a later simulation run generates
        for the same region. The optimum is the median (robust to a handful
        of misidentified outliers or records near cities/roads); the
        tolerance is the inter-quartile range converted to a Gaussian sigma,
        which is far less sensitive to outliers than the raw std deviation.

        Spatially thins the occurrences first (one per ~100km cell): GBIF's
        default result order is not a random sample, so without this a single
        densely-monitored dataset (one herbarium, one citizen-science project)
        can dominate the first page and make a widespread species look like a
        narrow specialist centered on wherever that one dataset happens to sit.

        Returns ``{}`` if fewer than :data:`MIN_OCCURRENCES_FOR_NICHE_FIT`
        occurrences have coordinates -- too few points to trust a fit.
        """
        if len(occurrences) < MIN_OCCURRENCES_FOR_NICHE_FIT:
            return {}

        thinned = self.spatial_thin(occurrences, grid_size_km=100.0)
        if len(thinned) >= MIN_OCCURRENCES_FOR_NICHE_FIT:
            occurrences = thinned

        lons = np.array([o.decimalLongitude for o in occurrences])
        lats = np.array([o.decimalLatitude for o in occurrences])
        temps, precips = self.climate_service.climate_at_points(lons, lats)

        def _opt_and_sigma(values: np.ndarray) -> tuple[float, float]:
            opt = float(np.median(values))
            q25, q75 = np.percentile(values, [25, 75])
            sigma = max(float(q75 - q25) / _IQR_TO_SIGMA, 1e-3)
            return opt, sigma

        t_opt, t_sigma = _opt_and_sigma(temps)
        p_opt, p_sigma = _opt_and_sigma(precips)

        return {
            "temperature_opt": t_opt,
            "temperature_sigma": t_sigma,
            "precipitation_opt": p_opt,
            "precipitation_sigma": p_sigma,
        }
