---
name: fetch-gbif-occurrences
version: 1.0.0
description: Fetch georeferenced species occurrence records from GBIF with spatial filtering and thinning
input_schema:
  type: object
  properties:
    species_name:
      type: string
      description: Scientific name of the species
    bbox:
      type: array
      items: number
      minItems: 4
      maxItems: 4
      description: Bounding box [west, south, east, north]
    year_range:
      type: object
      properties:
        start:
          type: integer
        end:
          type: integer
    grid_size_km:
      type: number
      default: 10.0
      description: Spatial thinning grid size in km
    limit:
      type: integer
      default: 5000
      maximum: 300000
---

# Fetch GBIF Occurrences

Retrieve georeferenced species occurrence records from the Global Biodiversity Information Facility (GBIF), with optional spatial thinning to reduce geographic bias.

## Input Parameters

- **species_name** (required): Scientific name (e.g., "Quercus alba")
- **bbox** (required): [west, south, east, north] in degrees
- **year_range** (optional): Filter occurrences by year
- **grid_size_km** (optional): Size of spatial thinning grid (default 10 km)
- **limit** (optional): Max records to fetch (default 5000, max 300000)

## Output

Returns a GeoJSON FeatureCollection with:
- Feature count
- Spatial coverage statistics
- Coordinate uncertainty estimates
- Thinning statistics (before/after counts)

## Use Cases

- Fitting species niche envelopes from occurrence data
- Validating simulation starting ranges
- Assessing sampling bias in species distribution records
- Calibrating dispersal models against observed ranges

## Example

```json
{
  "skill": "fetch-gbif-occurrences",
  "inputs": {
    "species_name": "Quercus alba",
    "bbox": [-125, 25, -66, 49],
    "grid_size_km": 10.0,
    "limit": 10000
  }
}
```
