"""GBIF API endpoints for species search and occurrence data."""

from fastapi import APIRouter, HTTPException, Query

from app.models.gbif import NicheParams, OccurrenceSearchRequest, OccurrenceSearchResponse, Taxon
from app.services.gbif_service import MIN_OCCURRENCES_FOR_NICHE_FIT, GBIFService

router = APIRouter(prefix="/gbif", tags=["GBIF"])
gbif_service = GBIFService()


@router.get("/taxa/search")
async def search_taxa(
    query: str = Query(..., min_length=1, description="Species name to search"),
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    """Search for taxa by scientific name."""
    try:
        results = await gbif_service.search_taxa(query, limit)
        return {"count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/occurrences/search")
async def search_occurrences(
    request: OccurrenceSearchRequest,
) -> OccurrenceSearchResponse:
    """Fetch occurrence records for a taxon."""
    try:
        response = await gbif_service.search_occurrences(
            taxon_key=request.taxon_key,
            limit=request.limit,
            geometry=request.geometry,
            year_start=request.year_start,
            year_end=request.year_end,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/occurrences/thin")
async def thin_occurrences(
    request: OccurrenceSearchRequest,
    grid_size_km: float = Query(10.0, gt=0, description="Grid cell size in km"),
) -> OccurrenceSearchResponse:
    """Fetch and spatially thin occurrence records."""
    try:
        response = await gbif_service.search_occurrences(
            taxon_key=request.taxon_key,
            limit=request.limit,
            geometry=request.geometry,
        )
        thinned = gbif_service.spatial_thin(response.results, grid_size_km)
        response.results = thinned
        response.count = len(thinned)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/niche/fit")
async def fit_niche_from_occurrences(
    request: OccurrenceSearchRequest,
) -> NicheParams:
    """Fit a niche envelope from a species' real GBIF occurrence records."""
    try:
        response = await gbif_service.search_occurrences(
            taxon_key=request.taxon_key,
            limit=request.limit,
            geometry=request.geometry,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GBIF lookup failed: {e}")

    niche = gbif_service.fit_niche(response.results)
    if not niche:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Only {response.count} geolocated occurrence(s) found "
                f"(need at least {MIN_OCCURRENCES_FOR_NICHE_FIT}) -- "
                "can't fit a reliable niche for this species"
            ),
        )

    return NicheParams(**niche)
