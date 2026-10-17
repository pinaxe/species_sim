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

import copy
from typing import Dict, List, Tuple

from .model import (
    DemographyParams,
    DispersalParams,
    InteractionEdge,
    NicheParams,
    SpeciesParams,
)

__all__ = [
    "PRESETS",
    "preset_names",
    "get_preset",
    "INTERACTION_PRESETS",
    "interaction_preset_names",
    "get_interaction_preset",
]


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
    return copy.deepcopy(PRESETS.get(name, PRESETS["Generic generalist"]))


# --------------------------------------------------------------------------- #
# Multi-species interaction presets
# --------------------------------------------------------------------------- #
#: Each entry is (species list, interaction edges) ready to hand to
#: ``MultiSpeciesSimulator`` -- a food web plus the per-species life history
#: that makes it behave sensibly (predators have lower ``r`` and ``K`` than
#: their prey, as in any real system).
INTERACTION_PRESETS: Dict[str, Tuple[List[SpeciesParams], List[InteractionEdge]]] = {
    "Fox and rabbit": (
        [
            SpeciesParams(
                name="Rabbit",
                niche=NicheParams(t_opt=14.0, t_tol=12.0, p_opt=900.0, p_tol=800.0),
                demography=DemographyParams(r=0.55, K=4000.0, mortality=0.05),
                dispersal=DispersalParams(sigma_km=15.0, kernel="gaussian", fraction=0.3),
                notes="Fast-breeding prey with a broad niche. Left alone it "
                      "saturates its carrying capacity; with foxes present its "
                      "equilibrium population settles well below K.",
            ),
            SpeciesParams(
                name="Fox",
                niche=NicheParams(t_opt=14.0, t_tol=15.0, p_opt=900.0, p_tol=900.0),
                demography=DemographyParams(r=0.15, K=300.0, mortality=0.17),
                dispersal=DispersalParams(sigma_km=35.0, kernel="exponential", fraction=0.4),
                notes="Slow-breeding predator: its own logistic term keeps it "
                      "bounded even before predation is considered, but without "
                      "rabbits to eat its mortality exceeding its growth rate "
                      "drives it to extinction (try it alone and watch it fade).",
            ),
        ],
        [
            # Rabbits lose growth in proportion to fox density (predation).
            InteractionEdge(affected="Rabbit", other="Fox", coefficient=-0.9),
            # Foxes gain growth in proportion to rabbit density, scaled down by
            # a conversion efficiency (most eaten biomass isn't converted to
            # new foxes). Tuned so the payoff is visible within ~100 steps:
            # with a smaller coefficient here the fox's intrinsic deficit
            # (mortality > r) dominates for 150+ steps before local rabbit
            # density gets high enough to flip it positive -- technically
            # correct Lotka-Volterra lag, but it reads as "the predator is
            # dying" in any normal-length demo run.
            InteractionEdge(affected="Fox", other="Rabbit", coefficient=0.6),
        ],
    ),
    "Lynx and snowshoe hare": (
        [
            SpeciesParams(
                name="Snowshoe hare",
                niche=NicheParams(t_opt=2.0, t_tol=10.0, p_opt=600.0, p_tol=400.0),
                demography=DemographyParams(r=0.7, K=5000.0, mortality=0.06),
                dispersal=DispersalParams(sigma_km=10.0, kernel="gaussian", fraction=0.25),
                notes="Classic boreal prey species; the Hudson's Bay Company "
                      "pelt records are the textbook example of this cycle.",
            ),
            SpeciesParams(
                name="Lynx",
                niche=NicheParams(t_opt=0.0, t_tol=12.0, p_opt=600.0, p_tol=450.0),
                demography=DemographyParams(r=0.18, K=200.0, mortality=0.2),
                dispersal=DispersalParams(sigma_km=40.0, kernel="exponential", fraction=0.35),
                notes="Specialist predator: strong coupling to hare density "
                      "produces the ~10-year boom-bust cycle seen in the field data.",
            ),
        ],
        [
            InteractionEdge(affected="Snowshoe hare", other="Lynx", coefficient=-1.1),
            # See the note on the fox/rabbit coefficient above -- same reasoning.
            InteractionEdge(affected="Lynx", other="Snowshoe hare", coefficient=0.6),
        ],
    ),
}


def interaction_preset_names() -> List[str]:
    return list(INTERACTION_PRESETS.keys())


def get_interaction_preset(name: str) -> Tuple[List[SpeciesParams], List[InteractionEdge]]:
    """Return a deep copy of a named food-web preset (species + interactions)."""
    species, edges = INTERACTION_PRESETS.get(
        name, INTERACTION_PRESETS["Fox and rabbit"]
    )
    return copy.deepcopy(species), copy.deepcopy(edges)
