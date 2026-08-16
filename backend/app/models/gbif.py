"""Pydantic models for GBIF data."""

from typing import Optional

from pydantic import BaseModel, Field


class Taxon(BaseModel):
    """GBIF taxon response."""

    key: int
    name: str
    canonicalName: Optional[str] = None
    datasetKey: Optional[str] = None
    nubKey: Optional[int] = None
    rank: Optional[str] = None


class Occurrence(BaseModel):
    """GBIF occurrence record."""

    key: int
    datasetKey: str
    scientificName: str
    decimalLatitude: float
    decimalLongitude: float
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    occurrenceStatus: str = "PRESENT"
    coordinateUncertaintyInMeters: Optional[float] = None


class OccurrenceSearchRequest(BaseModel):
    """Request to search GBIF occurrences."""

    taxon_key: int = Field(..., description="GBIF taxon key")
    limit: int = Field(10000, ge=1, le=300000, description="Max records to fetch")
    geometry: Optional[str] = Field(None, description="WKT polygon for spatial filter")
    year_start: Optional[int] = None
    year_end: Optional[int] = None


class OccurrenceSearchResponse(BaseModel):
    """Response from GBIF occurrence search."""

    count: int
    total: int
    limit: int
    offset: int
    results: list[Occurrence]
    taxon_name: str


class NicheParams(BaseModel):
    """Fitted niche parameters from occurrences."""

    temperature_opt: float = Field(..., description="Optimal temperature (°C)")
    temperature_sigma: float = Field(..., description="Temperature tolerance width (°C)")
    precipitation_opt: float = Field(..., description="Optimal precipitation (mm)")
    precipitation_sigma: float = Field(..., description="Precipitation tolerance (mm)")
    floor: float = Field(0.1, description="Habitat suitability floor")
