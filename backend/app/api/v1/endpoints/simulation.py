"""Simulation control endpoints with Server-Sent Events streaming."""

import asyncio
import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.models.simulation import SimulationConfig, SimulationResult
from app.services.simulation_service import SimulationService
from app.core.logging import get_logger

router = APIRouter(prefix="/simulation", tags=["Simulation"])
sim_service = SimulationService()
logger = get_logger(__name__)


@router.post("/estimate")
async def estimate_duration(config: SimulationConfig) -> dict:
    """Estimate simulation duration in seconds."""
    try:
        grid_size = int((config.bbox[2] - config.bbox[0]) / config.resolution_deg) * \
                    int((config.bbox[3] - config.bbox[1]) / config.resolution_deg)
        duration = sim_service.estimate_duration(config.n_steps, grid_size)
        return {
            "estimated_seconds": duration,
            "n_steps": config.n_steps,
            "grid_size": grid_size,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def simulation_stream(config: SimulationConfig) -> AsyncGenerator[str, None]:
    """Stream simulation progress as Server-Sent Events."""
    try:
        async for progress in sim_service.run_simulation(config):
            data = {
                "step": progress.step,
                "total_steps": progress.total_steps,
                "percent": progress.percent,
                "current_snapshot": progress.current_snapshot.model_dump(),
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0)
    except Exception as e:
        logger.error(f"Simulation stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/run")
@router.get("/run")
async def run_simulation(config: Optional[SimulationConfig] = None) -> StreamingResponse:
    """Run simulation and stream progress updates (GET for demo, POST for custom)."""
    if config is None:
        config = SimulationConfig(
            region="demo",
            species_name="Demo Species",
            bbox=(-125, 25, -66, 49),
            resolution_deg=0.25,
            temperature_opt=15,
            temperature_sigma=15,  # Wider tolerance
            precipitation_opt=1000,
            precipitation_sigma=500,  # Wider tolerance
            niche_floor=0.01,  # Lower floor so more cells are suitable
            carrying_capacity=1000,
            demography={"r": 0.1, "m": 0.05},
            dispersal={
                "kernel_type": "gaussian",
                "sigma": 10,
                "fraction": 0.1,
            },
            n_steps=50,
        )

    try:
        return StreamingResponse(
            simulation_stream(config),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/presets")
async def list_presets() -> dict:
    """List available simulation presets (curated scenarios)."""
    presets = {
        "contiguous_usa_oak": {
            "name": "White Oak (Contiguous USA)",
            "description": "Slow-dispersing, cold-tolerant oak",
            "region": "contiguous_usa",
            "bbox": [-125, 25, -66, 49],
            "species_name": "Quercus alba",
            "temperature_opt": 15.0,
            "temperature_sigma": 8.0,
            "precipitation_opt": 900,
            "precipitation_sigma": 300,
            "carrying_capacity": 100.0,
            "r": 0.05,
            "m": 0.02,
            "dispersal_kernel": "gaussian",
            "dispersal_sigma": 5.0,
            "dispersal_fraction": 0.05,
        },
        "contiguous_usa_mollusc": {
            "name": "Jump-dispersing Mollusk",
            "description": "Long-distance human-aided spread",
            "region": "contiguous_usa",
            "bbox": [-125, 25, -66, 49],
            "species_name": "Helix aspersum",
            "temperature_opt": 15.0,
            "temperature_sigma": 5.0,
            "precipitation_opt": 600,
            "precipitation_sigma": 200,
            "carrying_capacity": 500.0,
            "r": 0.2,
            "m": 0.1,
            "dispersal_kernel": "fat_tail",
            "dispersal_sigma": 50.0,
            "dispersal_fraction": 0.2,
            "alpha": 2.0,
            "stratified_fraction": 0.01,
            "jump_distance": 200.0,
        },
    }
    return {"presets": presets}


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str) -> dict:
    """Get a specific preset configuration."""
    presets = {
        "contiguous_usa_oak": {
            "name": "White Oak (Contiguous USA)",
            "bbox": [-125, 25, -66, 49],
            "temperature_opt": 15.0,
            "temperature_sigma": 8.0,
            "precipitation_opt": 900,
            "precipitation_sigma": 300,
            "carrying_capacity": 100.0,
            "r": 0.05,
            "m": 0.02,
        },
    }

    if preset_id not in presets:
        raise HTTPException(status_code=404, detail="Preset not found")

    return presets[preset_id]
