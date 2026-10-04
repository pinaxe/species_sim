"""High-level simulation management service."""

import asyncio
import time
from typing import AsyncGenerator, Optional

import numpy as np

from ..core.logging import get_logger
from ..models.simulation import (
    DemographyParams,
    DispersalParams,
    MultiSpeciesConfig,
    MultiSpeciesProgress,
    MultiSpeciesSnapshot,
    SimulationConfig,
    SimulationProgress,
    SimulationResult,
    SimulationSnapshot,
)
from ..sim_engine.data import load_environment, synthetic_environment
from ..sim_engine.model import (
    InteractionEdge,
    MultiSpeciesSimulator,
    Simulator,
    SpeciesParams,
    Environment,
    GridSpec,
    NicheParams as ModelNicheParams,
    DemographyParams as ModelDemographyParams,
    DispersalParams as ModelDispersalParams,
)
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

        # Create grid spec
        n_rows = len(env_data["lats"])
        n_cols = len(env_data["lons"])
        grid = GridSpec(
            west=config.bbox[0],
            south=config.bbox[1],
            east=config.bbox[2],
            north=config.bbox[3],
            n_rows=n_rows,
            n_cols=n_cols,
        )

        # Create environment
        env = Environment(
            grid=grid,
            temperature=env_data["temperature"],
            precipitation=env_data["precipitation"],
        )

        # Create niche parameters
        niche = ModelNicheParams(
            t_opt=config.temperature_opt,
            t_tol=config.temperature_sigma,
            p_opt=config.precipitation_opt,
            p_tol=config.precipitation_sigma,
        )

        # Create demography parameters
        demography = ModelDemographyParams(
            r=config.demography.r,
            K=config.carrying_capacity,
            mortality=config.demography.m,
            allee_threshold=config.demography.allee_threshold or 0.0,
        )

        # Create dispersal parameters
        dispersal = ModelDispersalParams(
            sigma_km=config.dispersal.sigma,
            kernel=config.dispersal.kernel_type,
            fraction=config.dispersal.fraction,
            truncate=3.0,
        )

        # Create species parameters
        species_params = SpeciesParams(
            name=config.species_name,
            niche=niche,
            demography=demography,
            dispersal=dispersal,
        )

        # Create simulator
        sim = Simulator(env, species_params)

        # Log suitability statistics for debugging
        suitable_cells = np.sum(sim.suitability > 0)
        logger.info(
            "Suitability check",
            suitable_cells=int(suitable_cells),
            total_cells=n_rows * n_cols,
            max_suitability=float(np.max(sim.suitability)),
            mean_suitability=float(np.mean(sim.suitability)),
        )

        # Seed initial population - try center first
        center_lon = (config.bbox[0] + config.bbox[2]) / 2
        center_lat = (config.bbox[1] + config.bbox[3]) / 2
        n0 = config.carrying_capacity * 0.1

        success = sim.seed(center_lon, center_lat, n0=n0)

        if not success:
            logger.warning("Seed failed at center, searching for suitable location")
            # Find a cell with maximum suitability
            if np.max(sim.suitability) > 0:
                max_suit_idx = np.unravel_index(np.argmax(sim.suitability), sim.suitability.shape)
                success = sim.seed_at(max_suit_idx[0], max_suit_idx[1], n0=n0)
                logger.info("Seeded at max suitability location", suitability=float(sim.suitability[max_suit_idx]))
            else:
                logger.error("No suitable cells found - niche too restrictive")

        if success:
            logger.info(
                "Population seeded successfully",
                species=config.species_name,
                initial_pop=float(np.sum(sim.N)),
            )
        else:
            logger.error("Failed to seed population after all attempts")

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

            # Record initial state (step 0) BEFORE any simulation
            initial_abundance = float(np.sum(sim.N))
            initial_cells = int(np.sum(sim.N > 0))
            logger.info(
                "Simulation starting",
                initial_population=initial_abundance,
                initial_cells=initial_cells,
                n_steps=config.n_steps,
            )

            for step in range(config.n_steps):
                # Run one step
                sim.step()

                # Compute metrics
                total_abundance = float(np.sum(sim.N))
                occupied_cells = int(np.sum(sim.N > 0))
                max_density = float(np.max(sim.N))

                if step == 0:
                    logger.info(
                        f"Step {step} completed",
                        population=total_abundance,
                        cells=occupied_cells,
                        density=max_density,
                    )

                # Compute front distance (simplified)
                occupied = np.where(sim.N > 0)
                if occupied_cells > 0 and len(occupied[0]) > 0:
                    center_row = np.mean(occupied[0])
                    max_row = np.max(occupied[0])
                    front_dist_cells = max_row - center_row
                    front_distance_km = front_dist_cells * 111 * config.resolution_deg
                else:
                    front_distance_km = 0.0

                # Sample occupied cells as sparse (lon, lat, population) points for map display
                population_points: list[list[float]] = []
                n_occupied = len(occupied[0])
                if n_occupied > 0:
                    rows, cols = occupied
                    max_points = 800
                    if n_occupied > max_points:
                        idx = np.random.choice(n_occupied, max_points, replace=False)
                        rows = rows[idx]
                        cols = cols[idx]
                    lons_arr = env.grid.lons
                    lats_arr = env.grid.lats
                    pops = sim.N[rows, cols]
                    population_points = [
                        [float(lons_arr[c]), float(lats_arr[r]), float(p)]
                        for r, c, p in zip(rows, cols, pops)
                    ]

                snapshot = SimulationSnapshot(
                    step=step,
                    time=step,
                    total_abundance=total_abundance,
                    occupied_cells=occupied_cells,
                    max_density=max_density,
                    front_distance_km=front_distance_km,
                    population_points=population_points,
                )
                snapshots.append(snapshot)

                progress = SimulationProgress(
                    step=step,
                    total_steps=config.n_steps,
                    percent=100.0 * step / config.n_steps,
                    current_snapshot=snapshot,
                )

                # Debug: log first and every 10th step
                if step == 0 or step % 10 == 0:
                    logger.info(
                        f"Yielding step {step}",
                        population=total_abundance,
                        cells=occupied_cells,
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

    @staticmethod
    def _population_points(
        sim: Simulator, env: Environment, max_points: int = 500
    ) -> tuple[list[list[float]], int, float]:
        """Sparse-sample a species' occupied cells as (lon, lat, pop) triples."""
        occupied = np.where(sim.N > 0)
        n_occupied = len(occupied[0])
        if n_occupied == 0:
            return [], 0, 0.0

        rows, cols = occupied
        if n_occupied > max_points:
            idx = np.random.choice(n_occupied, max_points, replace=False)
            rows, cols = rows[idx], cols[idx]

        lons_arr = env.grid.lons
        lats_arr = env.grid.lats
        pops = sim.N[rows, cols]
        points = [
            [float(lons_arr[c]), float(lats_arr[r]), float(p)]
            for r, c, p in zip(rows, cols, pops)
        ]
        return points, n_occupied, float(sim.N.max())

    async def prepare_multi_species_simulation(
        self,
        config: MultiSpeciesConfig,
    ) -> tuple[MultiSpeciesSimulator, Environment]:
        """Build a shared environment and a coupled multi-species simulator."""
        logger.info(
            "Loading environment for multi-species run",
            region=config.region,
            bbox=config.bbox,
            species=[s.name for s in config.species],
        )
        env_data = self.climate_service.get_procedural_climate(config.bbox, config.resolution_deg)

        n_rows = len(env_data["lats"])
        n_cols = len(env_data["lons"])
        grid = GridSpec(
            west=config.bbox[0],
            south=config.bbox[1],
            east=config.bbox[2],
            north=config.bbox[3],
            n_rows=n_rows,
            n_cols=n_cols,
        )
        env = Environment(
            grid=grid,
            temperature=env_data["temperature"],
            precipitation=env_data["precipitation"],
        )

        center_lon = (config.bbox[0] + config.bbox[2]) / 2
        center_lat = (config.bbox[1] + config.bbox[3]) / 2

        sims: dict[str, Simulator] = {}
        for sp in config.species:
            niche = ModelNicheParams(
                t_opt=sp.temperature_opt,
                t_tol=sp.temperature_sigma,
                p_opt=sp.precipitation_opt,
                p_tol=sp.precipitation_sigma,
                suitability_floor=sp.niche_floor,
            )
            demography = ModelDemographyParams(
                r=sp.demography.r,
                K=sp.carrying_capacity,
                mortality=sp.demography.m,
                allee_threshold=sp.demography.allee_threshold or 0.0,
            )
            dispersal = ModelDispersalParams(
                sigma_km=sp.dispersal.sigma,
                kernel=sp.dispersal.kernel_type,
                fraction=sp.dispersal.fraction,
                truncate=3.0,
                boundary=sp.dispersal.boundary_mode,
                jump_probability=sp.dispersal.stratified_fraction,
                jump_distance_km=sp.dispersal.jump_distance,
                fat_tail_alpha=sp.dispersal.alpha or 2.5,
            )
            species_params = SpeciesParams(
                name=sp.name, niche=niche, demography=demography, dispersal=dispersal
            )
            sim = Simulator(env, species_params)

            lon = sp.seed_x if sp.seed_x is not None else center_lon
            lat = sp.seed_y if sp.seed_y is not None else center_lat
            success = sim.seed(lon, lat, n0=sp.initial_population)
            if not success and np.max(sim.suitability) > 0:
                r, c = np.unravel_index(np.argmax(sim.suitability), sim.suitability.shape)
                success = sim.seed_at(r, c, n0=sp.initial_population)
            if not success:
                logger.warning("Failed to seed species", species=sp.name)

            sims[sp.name] = sim

        interactions = [
            InteractionEdge(affected=e.affected, other=e.other, coefficient=e.coefficient)
            for e in config.interactions
        ]
        multi = MultiSpeciesSimulator(sims, interactions)
        return multi, env

    async def run_multi_species_simulation(
        self,
        config: MultiSpeciesConfig,
    ) -> AsyncGenerator[MultiSpeciesProgress, None]:
        """Run a coupled multi-species simulation, yielding progress per step."""
        try:
            multi, env = await self.prepare_multi_species_simulation(config)

            logger.info(
                "Multi-species simulation starting",
                species=multi.names,
                n_steps=config.n_steps,
            )

            for step in range(config.n_steps):
                multi.step()

                species_snapshots: dict[str, SimulationSnapshot] = {}
                for name, sim in multi.sims.items():
                    points, occupied_cells, max_density = self._population_points(sim, env)
                    species_snapshots[name] = SimulationSnapshot(
                        step=step,
                        time=step,
                        total_abundance=float(sim.N.sum()),
                        occupied_cells=occupied_cells,
                        max_density=max_density,
                        front_distance_km=sim.metrics[-1].front_km if sim.metrics else 0.0,
                        population_points=points,
                    )

                snapshot = MultiSpeciesSnapshot(step=step, time=step, species=species_snapshots)
                yield MultiSpeciesProgress(
                    step=step,
                    total_steps=config.n_steps,
                    percent=100.0 * step / config.n_steps,
                    current_snapshot=snapshot,
                )
                await asyncio.sleep(0)  # allow cancellation

            logger.info("Multi-species simulation complete", steps=config.n_steps)

        except Exception as e:
            logger.error(f"Multi-species simulation failed: {e}")
            raise

    def estimate_duration(self, n_steps: int, grid_size: int) -> float:
        """Estimate simulation duration in seconds."""
        # ~500 steps/sec on 104×236 grid with modern CPU
        steps_per_sec = 500
        return n_steps / steps_per_sec * (grid_size / 104)
