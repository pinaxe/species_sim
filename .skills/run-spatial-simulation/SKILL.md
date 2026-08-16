---
name: run-spatial-simulation
version: 1.0.0
description: Execute vectorized species dispersal simulation with Gaussian niche and reaction-diffusion dynamics
input_schema:
  type: object
  properties:
    species_name:
      type: string
    bbox:
      type: array
      items: number
      minItems: 4
      maxItems: 4
    niche:
      type: object
      properties:
        temperature_opt:
          type: number
        temperature_sigma:
          type: number
        precipitation_opt:
          type: number
        precipitation_sigma:
          type: number
    demography:
      type: object
      properties:
        r:
          type: number
          description: Growth rate
        m:
          type: number
          description: Mortality rate
        K:
          type: number
          description: Carrying capacity
    dispersal:
      type: object
      properties:
        kernel:
          type: string
          enum: [gaussian, exponential, fat_tail]
        sigma_km:
          type: number
        fraction:
          type: number
    n_steps:
      type: integer
      default: 100
---

# Run Spatial Simulation

Execute a high-performance vectorized simulation of species dispersal and range expansion using a reaction-diffusion model on a geographic grid.

## Model

**1. Habitat Suitability** — Gaussian envelope over temperature and precipitation:

S(x,y) = exp(-(T-T_opt)²/2σ_T²) × exp(-(P-P_opt)²/2σ_P²)

**2. Local Dynamics** — Discrete logistic growth scaled by suitability:

N_{t+1} = N_t + r·N_t·(1 - N_t/K·S) - m·N_t

**3. Dispersal** — Convolution with normalized kernel (Gaussian/Exponential/Fat-tail):

- Gaussian: e^(-d²/2σ²) — smooth travelling wave
- Exponential: e^(-d/σ) — accelerated spread  
- Fat-tail: (1+d/σ)^(-α) — satellite colonies

## Input Parameters

- **niche**: Optimal conditions and tolerance
  - `temperature_opt`, `precipitation_opt` — niche center
  - Sigma parameters — tolerance width
- **demography**: Population dynamics
  - `r` — intrinsic growth rate
  - `m` — natural mortality
  - `K` — carrying capacity
- **dispersal**: Movement kernel (km-based, isotropic on ground)
- **n_steps**: Simulation length (default 100)

## Output

Streaming GeoJSON with per-step snapshots:
- Population density grid
- Invasion metrics (area, total abundance, front distance)
- Timing and progression statistics

## Performance

~500–750 steps/second on 104×236 grid (NumPy/SciPy vectorized)

## Example

```json
{
  "skill": "run-spatial-simulation",
  "inputs": {
    "species_name": "Quercus alba",
    "bbox": [-125, 25, -66, 49],
    "niche": {
      "temperature_opt": 15,
      "temperature_sigma": 8,
      "precipitation_opt": 900,
      "precipitation_sigma": 300
    },
    "demography": {"r": 0.05, "m": 0.02, "K": 1000},
    "dispersal": {"kernel": "gaussian", "sigma_km": 10, "fraction": 0.1},
    "n_steps": 100
  }
}
```
