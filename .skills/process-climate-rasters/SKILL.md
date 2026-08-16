---
name: process-climate-rasters
version: 1.0.0
description: Clip, normalize, and reproject climate/environmental rasters to a region
input_schema:
  type: object
  properties:
    layers:
      type: array
      items:
        type: string
      description: Climate layer names (temperature, precipitation, etc.)
    bbox:
      type: array
      items: number
      minItems: 4
      maxItems: 4
      description: Bounding box [west, south, east, north]
    resolution_deg:
      type: number
      default: 0.25
      description: Output resolution in degrees
    normalization:
      type: string
      enum: [none, minmax, zscore]
      default: minmax
---

# Process Climate Rasters

Clip, reproject, and normalize climate layers (WorldClim, DEM, etc.) for use in species simulation. Handles geospatial data ingestion and standardization.

## Input Parameters

- **layers** (required): Array of layer names to process
  - `temperature` — mean annual temperature (°C)
  - `precipitation` — total annual precipitation (mm)
  - `elevation` — digital elevation model (m)
- **bbox** (required): [west, south, east, north] in degrees
- **resolution_deg** (optional): Output grid resolution (default 0.25°)
- **normalization** (optional): Scaling method for environmental variables

## Output

Returns a GeoJSON-formatted raster grid with:
- Clipped layer values
- Layer metadata (min, max, mean, units)
- Coordinate reference system info
- Data quality flags

## Use Cases

- Preparing climate input for species simulations
- Converting between WorldClim versions (v1/v2)
- Masking ocean cells and creating coastlines
- Resampling rasters to consistent resolution

## Example

```json
{
  "skill": "process-climate-rasters",
  "inputs": {
    "layers": ["temperature", "precipitation"],
    "bbox": [-125, 25, -66, 49],
    "resolution_deg": 0.25,
    "normalization": "minmax"
  }
}
```
