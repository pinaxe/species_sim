"""High-level simulation management service."""

import asyncio
import time
from typing import AsyncGenerator, Optional

import numpy as np

from ..core.logging import get_logger
from ..models.simulation import (
    DemographyParams,
    DispersalParams,
    SimulationConfig,
    SimulationProgress,
    SimulationResult,
    SimulationSnapshot,
)
from ..sim_engine.data import load_environment, procedural_climate
from ..sim_engine.model import Simulator, SpeciesParams, Environment, DemographyParams as ModelDemographyParams
from .climate_service import ClimateService

logger = get_logger(__name__)


class SimulationService:
    """Orchestrate species dispersal simulations."""

    def __init__(self):
        self.climate_service = ClimateService()

    async def prepare_simulation(
        self,
        config: SimulationConfig,
    ) -> tuple[Simulator, Environment, np.ndarray]:
        """Prepare a simulation from configuration."""
        # Get environment data
        logger.info("Loading environment", region=config.region, bbox=config.bbox)
        env_data = self.climate_service.get_procedural_climate(config.bbox, config.resolution_deg)

        env = Environment(
            rows=len(env_data["lats"]),
            cols=len(env_data["lons"]),
            temperature=env_data["temperature"],
            precipitation=env_data["precipitation"],
            ocean=np.zeros_like(env_data["temperature"], dtype=bool),
        )

        species_params = SpeciesParams(
            K=config.carrying_capacity,
            T_opt=config.temperature_opt,
            T_sd=config.temperature_sigma,
            P_opt=config.precipitation_opt,
            P_sd=config.precipitation_sigma,
            suitability_floor=config.niche_floor,
        )

        demography = ModelDemographyParams(
            r=config.demography.r,
            m=config.demography.m,
            allee=config.demography.allee_threshold,
        )

        dispersal = {
            "kernel_type": config.dispersal.kernel_type,
            "sigma": config.dispersal.sigma,
            "fraction": config.dispersal.fraction,
            "alpha": config.dispersal.alpha,
            "stratified_fraction": config.dispersal.stratified_fraction,
            "jump_distance": config.dispersal.jump_distance,
        }

        # Create simulator
        sim = Simulator(env, species_params, demography, dispersal)

        # Seed initial population
        if config.seed_x is not None and config.seed_y is not None:
            row = int((config.seed_y - env_data["lats"][0]) / config.resolution_deg)
            col = int((config.seed_x - env_data["lons"][0]) / config.resolution_deg)
            if 0 <= row < env.rows and 0 <= col < env.cols:
                sim.population[row, col] = config.carrying_capacity * 0.1
                logger.info("Seeded population", row=row, col=col)

        return sim, env, env_data["lats"]

    async def run_simulation(
        self,
        config: SimulationConfig,
    ) -> AsyncGenerator[SimulationProgress, None]:
        """Run simulation and yield progress updates."""
        start_time = time.time()

        try:
            sim, env, lats = await self.prepare_simulation(config)

            snapshots = []
            for step in range(config.n_steps):
                # Run one step
                sim.step()

                # Compute metrics
                total_abundance = float(np.sum(sim.population))
                occupied_cells = int(np.sum(sim.population > 0))
                max_density = float(np.max(sim.population))

                # Compute front distance (simplified)
                if occupied_cells > 0:
                    occupied = np.where(sim.population > 0)
                    if len(occupied[0]) > 0:
                        center_row = np.mean(occupied[0])
                        max_row = np.max(occupied[0])
                        front_dist_cells = max_row - center_row
                        front_distance_km = front_dist_cells * 111 * config.resolution_deg
                    else:
                        front_distance_km = 0.0
                else:
                    front_distance_km = 0.0

                snapshot = SimulationSnapshot(
                    step=step,
                    time=step,
                    total_abundance=total_abundance,
                    occupied_cells=occupied_cells,
                    max_density=max_density,
                    front_distance_km=front_distance_km,
                )
                snapshots.append(snapshot)

                progress = SimulationProgress(
                    step=step,
                    total_steps=config.n_steps,
                    percent=100.0 * step / config.n_steps,
                    current_snapshot=snapshot,
                )

                yield progress

                await asyncio.sleep(0)  # Allow cancellation

            duration = time.time() - start_time
            logger.info(
                "Simulation complete",
                steps=config.n_steps,
                duration=duration,
                final_abundance=snapshots[-1].total_abundance if snapshots else 0,
            )

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            raise

    def estimate_duration(self, n_steps: int, grid_size: int) -> float:
        """Estimate simulation duration in seconds."""
        # ~500 steps/sec on 104×236 grid with modern CPU
        steps_per_sec = 500
        return n_steps / steps_per_sec * (grid_size / 104)
