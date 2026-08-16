"""Simulation engine core (vectorized NumPy/SciPy)."""

from .model import Simulator, SpeciesParams, Environment, DemographyParams, DispersalParams
from .data import load_environment, procedural_climate
from .species import get_preset, preset_names

__all__ = [
    "Simulator",
    "SpeciesParams",
    "Environment",
    "DemographyParams",
    "DispersalParams",
    "load_environment",
    "procedural_climate",
    "get_preset",
    "preset_names",
]
