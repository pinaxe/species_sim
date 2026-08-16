"""FastMCP Server for BioSim-Engine - exposes simulation as AI agent tools."""

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BioSim-Engine")


@mcp.tool()
def search_species(query: str) -> str:
    """Search for species by scientific name on GBIF.

    Args:
        query: Species scientific name (e.g., "Quercus alba")

    Returns:
        JSON-formatted list of matching taxa with keys
    """
    # In production, call backend API
    return json.dumps({
        "status": "success",
        "message": f"Searched for {query} (mock)",
        "results": []
    })


@mcp.tool()
def fetch_occurrences(species_key: int, bbox: str, limit: int = 5000) -> str:
    """Fetch georeferenced occurrence records for a species.

    Args:
        species_key: GBIF taxon key
        bbox: Bounding box as "west,south,east,north"
        limit: Maximum records to fetch (default 5000)

    Returns:
        JSON with occurrence points and spatial summary
    """
    return json.dumps({
        "status": "success",
        "count": 0,
        "records": []
    })


@mcp.tool()
def get_climate_layers(bbox: str) -> str:
    """Get available climate/environmental layers for a region.

    Args:
        bbox: Bounding box as "west,south,east,north"

    Returns:
        JSON list of available climate layers with metadata
    """
    return json.dumps({
        "layers": [
            {"name": "temperature", "unit": "°C", "resolution": "0.25°"},
            {"name": "precipitation", "unit": "mm", "resolution": "0.25°"}
        ]
    })


@mcp.tool()
def estimate_simulation(
    n_steps: int,
    grid_resolution: float,
    region_size_deg2: float
) -> str:
    """Estimate simulation runtime.

    Args:
        n_steps: Number of time steps
        grid_resolution: Grid cell size (degrees)
        region_size_deg2: Region area (square degrees)

    Returns:
        JSON with estimated duration in seconds
    """
    # Rough estimate: 500 steps/sec on 104×236 grid
    grid_cells = region_size_deg2 / (grid_resolution ** 2)
    steps_per_sec = max(10, 500 * (104*236) / grid_cells)
    duration = n_steps / steps_per_sec

    return json.dumps({
        "estimated_seconds": duration,
        "grid_cells": int(grid_cells),
        "steps": n_steps
    })


@mcp.tool()
def run_simulation(
    species_name: str,
    bbox: str,
    temperature_opt: float,
    temperature_sigma: float,
    precipitation_opt: float,
    precipitation_sigma: float,
    n_steps: int = 100,
    carrying_capacity: float = 1000.0,
    growth_rate: float = 0.1,
    mortality_rate: float = 0.05,
    dispersal_fraction: float = 0.1,
    dispersal_sigma_km: float = 10.0
) -> str:
    """Run a species dispersal simulation.

    Args:
        species_name: Scientific name
        bbox: Bounding box as "west,south,east,north"
        temperature_opt: Optimal temperature (°C)
        temperature_sigma: Temperature tolerance (°C)
        precipitation_opt: Optimal precipitation (mm)
        precipitation_sigma: Precipitation tolerance (mm)
        n_steps: Number of simulation steps
        carrying_capacity: Maximum density per grid cell
        growth_rate: Intrinsic growth rate (per step)
        mortality_rate: Natural mortality rate
        dispersal_fraction: Fraction of population dispersing
        dispersal_sigma_km: Dispersal distance (km)

    Returns:
        JSON with simulation results and invasion metrics
    """
    return json.dumps({
        "status": "simulation-queued",
        "species": species_name,
        "task_id": "abc123",
        "steps": n_steps,
        "message": "Simulation queued (mock)"
    })


@mcp.tool()
def analyze_invasion_risk(
    species_name: str,
    bbox: str,
    occurrence_points: int
) -> str:
    """Analyze invasion risk based on species niche and climate.

    Args:
        species_name: Scientific name
        bbox: Study region as "west,south,east,north"
        occurrence_points: Number of known occurrences

    Returns:
        JSON with risk assessment and suitable habitat area
    """
    return json.dumps({
        "species": species_name,
        "risk_score": 0.65,
        "suitable_area_pct": 35.2,
        "invasion_front_km": 125.3,
        "recommendations": [
            "Monitor northern range edge",
            "Consider climate-adapted barriers"
        ]
    })


if __name__ == "__main__":
    # Run with: python -m mcp_server.server
    # Or via stdio for IDE integration
    mcp.run()
