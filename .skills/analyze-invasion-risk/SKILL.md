---
name: analyze-invasion-risk
version: 1.0.0
description: Assess invasion risk and suitable habitat from simulated range and climate
input_schema:
  type: object
  properties:
    species_name:
      type: string
    simulation_result:
      type: object
      description: Output from run-spatial-simulation
    climate_extent:
      type: array
      items: number
      minItems: 4
      maxItems: 4
---

# Analyze Invasion Risk

Compute invasion metrics from simulation results and climate data: suitable habitat extent, range expansion velocity, and risk scoring for management.

## Metrics Computed

**Range Metrics:**
- Occupied area (km²)
- Distance from introduction point (km)
- Range expansion velocity (km/year)
- Colonization rate (new cells/year)

**Suitability Metrics:**
- Fraction of region with suitable climate
- Core vs. marginal habitat (by suitability)
- Refugee habitat (climatically stable over time)

**Risk Scores:**
- Invasion speed (0–1, faster = higher risk)
- Habitat availability (0–1, more suitable = higher risk)
- Uncertainty in niche fit (0–1)
- Overall risk (weighted combination)

## Output

JSON object with:
```json
{
  "species": "...",
  "suitable_area_pct": 35.2,
  "invasion_front_km": 125.3,
  "expansion_velocity_km_year": 8.5,
  "risk_score": 0.65,
  "recommendations": [...]
}
```

## Use Cases

- Prioritizing species for monitoring/control
- Identifying range expansion fronts for management intervention
- Assessing climate-driven range shifts
- Benchmarking against historical invasions

## Example

```json
{
  "skill": "analyze-invasion-risk",
  "inputs": {
    "species_name": "Quercus alba",
    "simulation_result": {...simulation output...},
    "climate_extent": [-125, 25, -66, 49]
  }
}
```
