"""Simulation engine core (vectorized NumPy/SciPy)."""

from .model import Simulator, SpeciesParams, Environment, DemographyParams, DispersalParams
from .data import load_environment, synthetic_environment
from .species import get_preset, preset_names

__all__ = [
    "Simulator",
    "SpeciesParams",
    "Environment",
    "DemographyParams",
    "DispersalParams",
    "load_environment",
    "synthetic_environment",
    "get_preset",
    "preset_names",
]
