"""Pydantic models for simulation configuration and output."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DispersalKernelType(str):
    """Types of dispersal kernels."""
    gaussian = "gaussian"
    exponential = "exponential"
    fat_tail = "fat_tail"


class DispersalParams(BaseModel):
    """Dispersal parameters."""

    kernel_type: str = Field("gaussian", description="gaussian | exponential | fat_tail")
    sigma: float = Field(10.0, gt=0, description="Kernel spread (km)")
    fraction: float = Field(0.1, ge=0, le=1, description="Fraction dispersing per step")
    alpha: Optional[float] = Field(None, description="Fat-tail power (only for fat_tail)")
    stratified_fraction: float = Field(0.0, ge=0, le=1, description="Jump dispersal fraction")
    jump_distance: float = Field(100.0, gt=0, description="Jump distance (km)")
    boundary_mode: str = Field("reflecting", description="reflecting | absorbing")


class DemographyParams(BaseModel):
    """Demographic parameters."""

    r: float = Field(0.1, ge=0, description="Intrinsic growth rate")
    m: float = Field(0.05, ge=0, le=1, description="Natural mortality rate")
    allee_threshold: Optional[float] = Field(None, ge=0, description="Minimum viable population")


class SimulationConfig(BaseModel):
    """Complete simulation configuration."""

    region: str = Field(..., description="Region name (e.g., 'contiguous_usa')")
    species_name: str = Field(..., description="Species scientific name")
    bbox: tuple[float, float, float, float] = Field(..., description="(west, south, east, north)")
    resolution_deg: float = Field(0.25, gt=0, description="Grid resolution (degrees)")

    # Environmental suitability
    temperature_opt: float = Field(..., description="Optimal temperature (°C)")
    temperature_sigma: float = Field(..., description="Temperature tolerance (°C)")
    precipitation_opt: float = Field(..., description="Optimal precipitation (mm)")
    precipitation_sigma: float = Field(..., description="Precipitation tolerance (mm)")
    niche_floor: float = Field(0.1, ge=0, le=1, description="Suitability floor")

    # Dynamics
    carrying_capacity: float = Field(1000.0, gt=0, description="Max density per cell")
    demography: DemographyParams
    dispersal: DispersalParams

    # Simulation control
    n_steps: int = Field(100, gt=0, description="Number of time steps")
    seed_x: Optional[float] = None
    seed_y: Optional[float] = None


class SimulationSnapshot(BaseModel):
    """Simulation state at one time step."""

    step: int
    time: int
    total_abundance: float
    occupied_cells: int
    max_density: float
    front_distance_km: float
    grid_data: Optional[list[list[float]]] = None  # Sparse encoding recommended


class SimulationProgress(BaseModel):
    """Progress update during simulation."""

    step: int
    total_steps: int
    percent: float
    current_snapshot: SimulationSnapshot


class SimulationResult(BaseModel):
    """Final simulation result."""

    config: SimulationConfig
    snapshots: list[SimulationSnapshot]
    final_metrics: dict
    run_duration_seconds: float
