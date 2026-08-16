"""
species.py
==========

Parameter presets for a handful of well-studied invaders plus generic
life-history archetypes.

Values are order-of-magnitude sensible rather than calibrated: they give the
right *qualitative* behaviour (a thermophilic insect races north through a
warm summer landscape; a cold-adapted conifer creeps). Treat them as starting
points and refit against real demographic data before drawing conclusions.

``r`` and ``mortality`` are per *time step*; a step is whatever you declare it
to be (the UI labels steps as years by default, so ``r=0.6`` means a ~80%
annual intrinsic increase).
"""

from __future__ import annotations

from typing import Dict, List

from model import DemographyParams, DispersalParams, NicheParams, SpeciesParams

__all__ = ["PRESETS", "preset_names", "get_preset"]


PRESETS: Dict[str, SpeciesParams] = {
    "Generic generalist": SpeciesParams(
        name="Generic generalist",
        niche=NicheParams(t_opt=16.0, t_tol=10.0, p_opt=900.0, p_tol=900.0),
        demography=DemographyParams(r=0.35, K=1000.0, mortality=0.03),
        dispersal=DispersalParams(sigma_km=25.0, kernel="gaussian", fraction=0.25),
        notes="Broad tolerances, moderate spread. A good baseline for exploring "
              "how the other sliders behave.",
    ),
    "Thermophilic insect": SpeciesParams(
        name="Thermophilic insect",
        niche=NicheParams(t_opt=24.0, t_tol=5.0, p_opt=1100.0, p_tol=800.0),
        demography=DemographyParams(r=0.85, K=5000.0, mortality=0.10),
        dispersal=DispersalParams(sigma_km=18.0, kernel="exponential", fraction=0.35),
        notes="High r, leptokurtic flight dispersal, narrow thermal window. "
              "Shows a sharp, fast travelling wave that stalls at a thermal edge.",
    ),
    "Wind-dispersed weed": SpeciesParams(
        name="Wind-dispersed weed",
        niche=NicheParams(t_opt=17.0, t_tol=8.0, p_opt=700.0, p_tol=500.0),
        demography=DemographyParams(r=0.60, K=2500.0, mortality=0.06),
        dispersal=DispersalParams(
            sigma_km=12.0, kernel="fat_tail", fraction=0.40, fat_tail_alpha=2.2
        ),
        notes="Power-law tail: expect patchy satellite populations well ahead of "
              "the main front, and accelerating (non-constant) spread rate.",
    ),
    "Slow-spreading conifer": SpeciesParams(
        name="Slow-spreading conifer",
        niche=NicheParams(t_opt=7.0, t_tol=5.0, p_opt=1400.0, p_tol=700.0),
        demography=DemographyParams(r=0.12, K=400.0, mortality=0.01),
        dispersal=DispersalParams(sigma_km=6.0, kernel="gaussian", fraction=0.12),
        notes="Cold-adapted, low r, short kernel. Range shifts on a century "
              "timescale; useful for demonstrating dispersal limitation.",
    ),
    "Freshwater mollusc (human-mediated)": SpeciesParams(
        name="Freshwater mollusc (human-mediated)",
        niche=NicheParams(t_opt=14.0, t_tol=7.0, p_opt=1000.0, p_tol=900.0),
        demography=DemographyParams(r=0.70, K=8000.0, mortality=0.08),
        dispersal=DispersalParams(
            sigma_km=8.0,
            kernel="exponential",
            fraction=0.15,
            jump_probability=0.02,
            jump_distance_km=350.0,
        ),
        notes="Short natural kernel plus rare long-distance jumps on boat hulls. "
              "Stochastic: reruns differ. This is the classic stratified-diffusion "
              "invasion pattern.",
    ),
    "Tropical specialist": SpeciesParams(
        name="Tropical specialist",
        niche=NicheParams(t_opt=26.0, t_tol=3.0, p_opt=2200.0, p_tol=600.0),
        demography=DemographyParams(r=0.50, K=1500.0, mortality=0.05),
        dispersal=DispersalParams(sigma_km=15.0, kernel="gaussian", fraction=0.20),
        notes="Very narrow niche on both axes. Often fails to establish at all "
              "outside the wet tropics -- a useful negative control.",
    ),
    "Arid-zone shrub": SpeciesParams(
        name="Arid-zone shrub",
        niche=NicheParams(t_opt=21.0, t_tol=8.0, p_opt=280.0, p_tol=200.0),
        demography=DemographyParams(r=0.25, K=600.0, mortality=0.02),
        dispersal=DispersalParams(sigma_km=10.0, kernel="fat_tail", fraction=0.18),
        notes="Precipitation-limited rather than temperature-limited; watch the "
              "suitability map invert relative to the other presets.",
    ),
}


def preset_names() -> List[str]:
    return list(PRESETS.keys())


def get_preset(name: str) -> SpeciesParams:
    """Return a *copy* of a preset so UI edits never mutate the table."""
    import copy

    return copy.deepcopy(PRESETS.get(name, PRESETS["Generic generalist"]))
