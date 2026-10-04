"""Pydantic models for simulation configuration and output."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


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
    population_points: Optional[list[list[float]]] = None  # [lon, lat, population] triples


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


# --------------------------------------------------------------------------- #
# Multi-species (interacting populations)
# --------------------------------------------------------------------------- #
class InteractionConfig(BaseModel):
    """One directed pairwise Lotka-Volterra term between two species in a run.

    Every step, ``affected``'s per-cell growth gets an extra
    ``coefficient * N_affected * (N_other / K_other)``. A predator-prey pair is
    two edges: a negative one on the prey (eaten) and a smaller positive one
    on the predator (only part of what's eaten becomes new predators).
    """

    affected: str = Field(..., description="Name of the species whose growth this edge modifies")
    other: str = Field(..., description="Name of the species this edge reacts to")
    coefficient: float = Field(
        ..., description="Per-capita effect; negative = harmed (prey), positive = benefits (predator)"
    )


class SpeciesConfig(BaseModel):
    """One species within a multi-species simulation run."""

    name: str = Field(..., description="Species identifier, referenced by InteractionConfig")
    temperature_opt: float = Field(..., description="Optimal temperature (°C)")
    temperature_sigma: float = Field(..., description="Temperature tolerance (°C)")
    precipitation_opt: float = Field(..., description="Optimal precipitation (mm)")
    precipitation_sigma: float = Field(..., description="Precipitation tolerance (mm)")
    niche_floor: float = Field(0.02, ge=0, le=1, description="Suitability floor")
    carrying_capacity: float = Field(..., gt=0, description="Max density per cell")
    demography: DemographyParams
    dispersal: DispersalParams
    initial_population: float = Field(100.0, gt=0, description="Founding population size (n0)")
    seed_x: Optional[float] = None
    seed_y: Optional[float] = None


class MultiSpeciesConfig(BaseModel):
    """Complete configuration for a coupled multi-species simulation run."""

    region: str = Field(..., description="Region name (e.g., 'contiguous_usa')")
    bbox: tuple[float, float, float, float] = Field(..., description="(west, south, east, north)")
    resolution_deg: float = Field(0.25, gt=0, description="Grid resolution (degrees)")
    species: list[SpeciesConfig] = Field(..., min_length=1)
    interactions: list[InteractionConfig] = Field(default_factory=list)
    n_steps: int = Field(100, gt=0, description="Number of time steps")

    @model_validator(mode="after")
    def _names_are_unique_and_edges_resolve(self) -> "MultiSpeciesConfig":
        names = [s.name for s in self.species]
        if len(names) != len(set(names)):
            raise ValueError("species names must be unique")
        unknown = {
            n
            for edge in self.interactions
            for n in (edge.affected, edge.other)
            if n not in names
        }
        if unknown:
            raise ValueError(f"interactions reference unknown species: {sorted(unknown)}")
        return self


class MultiSpeciesSnapshot(BaseModel):
    """Simulation state at one time step, across all species."""

    step: int
    time: int
    species: dict[str, SimulationSnapshot]


class MultiSpeciesProgress(BaseModel):
    """Progress update during a multi-species simulation."""

    step: int
    total_steps: int
    percent: float
    current_snapshot: MultiSpeciesSnapshot
