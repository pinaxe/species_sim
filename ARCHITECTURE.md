# BioSim-Engine Architecture

A production-grade, agent-ready species dispersal and ecological simulator combining high-performance vectorized simulation with modern web infrastructure.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent (MCP Client)                     │
│                  (Claude, Other LLMs)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                    MCP Protocol
                         │
        ┌────────────────┴────────────────┐
        ▼                                  ▼
┌──────────────────┐              ┌──────────────────┐
│   MCP Server     │              │  FastAPI Backend │
│  (Tools Export)  │              │  (REST API)      │
└──────────────────┘              └────────┬─────────┘
                                           │
        ┌──────────────────────────────────┼──────────────────────────────┐
        │                                  │                              │
        ▼                                  ▼                              ▼
┌─────────────────┐         ┌──────────────────────┐         ┌────────────────┐
│  Redis Cache    │         │ Simulation Engine    │         │ Data Services  │
│ (Session State) │         │  (NumPy/SciPy Core)  │         │ (GBIF/Climate) │
└─────────────────┘         └──────────────────────┘         └────────────────┘
                                      │
                                      ▼
                         ┌──────────────────────┐
                         │  Next.js Frontend    │
                         │ (Interactive UI)     │
                         └──────────────────────┘
```

## Layer Architecture

### 1. Core Simulation Engine (`backend/app/sim_engine/`)

**Pure NumPy/SciPy vectorized computation** — no external dependencies beyond scientific stack.

- **`model.py`** — Reaction-diffusion simulator
  - Habitat suitability (Gaussian niche envelope)
  - Discrete logistic growth (local dynamics)
  - Dispersal kernel convolution (Gaussian, Exponential, Fat-tail)
  - Boundary conditions (reflecting/absorbing)
  - Performance: ~500–750 steps/sec on 104×236 grid

- **`data.py`** — Environmental data management
  - Procedural climate generator (fallback)
  - GeoTIFF raster loader (rasterio)
  - GBIF occurrence fetcher (pygbif)
  - Spatial thinning (grid-based debiasing)

- **`species.py`** — Parameter presets
  - 7 calibrated species templates
  - Niche ranges from fast-dispersers to slow-costers

### 2. FastAPI Backend (`backend/app/`)

RESTful API wrapping the simulation engine with async/await, caching, and streaming.

#### Core Modules

- **`core/`** — Configuration & infrastructure
  - `config.py` — Pydantic Settings from environment
  - `logging.py` — Structured JSON logging (structlog)
  - `redis.py` — Async Redis client & caching

- **`models/`** — Request/response validation (Pydantic v2)
  - `gbif.py` — Taxa and occurrence schemas
  - `raster.py` — Climate layer metadata
  - `simulation.py` — Configuration and result schemas

- **`services/`** — Business logic
  - `gbif_service.py` — GBIF API client, spatial thinning, niche fitting
  - `climate_service.py` — Raster clipping, normalization, procedural fallback
  - `simulation_service.py` — High-level orchestration

- **`api/v1/endpoints/`** — Route handlers
  - `gbif.py` — Species search, occurrence fetching
  - `rasters.py` — Layer listing, clipping
  - `simulation.py` — Simulation triggers, Server-Sent Events (SSE) streaming

#### Key Features

- **Streaming progress** — SSE for real-time simulation updates
- **Smart caching** — Redis for GBIF queries, raster clips
- **Fallback behavior** — Procedural climate when rasterio unavailable
- **CORS-enabled** — Ready for web frontend

### 3. Background Workers (`backend/app/workers/`)

Celery + Redis for long-running simulations outside the HTTP request/response cycle.

- Task queue for multi-hour simulations
- Result persistence
- Progress tracking
- (Scaffold in place; production implementation pending)

### 4. Agent Skills (`.skills/*/SKILL.md`)

OpenAgent / Agent Skills specification for AI agent integration.

1. **`fetch-gbif-occurrences`** — Get georeferenced records
2. **`process-climate-rasters`** — Clip & reproject climate layers
3. **`run-spatial-simulation`** — Execute dispersal model
4. **`analyze-invasion-risk`** — Compute metrics from results

Each skill is self-contained, versioned, and describes I/O schema + examples.

### 5. MCP Server (`mcp_server/`)

Model Context Protocol server exposing simulation as callable tools for Claude and other LLMs.

- Tools: `search_species`, `fetch_occurrences`, `run_simulation`, `analyze_invasion_risk`
- Stdio transport for IDE integration
- SSE transport for remote AI applications

### 6. Next.js Frontend (`frontend/`)

Modern React 18 + TypeScript + Tailwind CSS web UI.

#### Structure

- **`app/`** — Next.js 14 App Router
  - `layout.tsx` — Root layout & metadata
  - `page.tsx` — Master dashboard

- **`components/`**
  - `map/` — MapLibre GL + Deck.gl canvas for spatial visualization
  - `panels/` — Sidebar (wizard), Analytics, Parameter controls
  - `hud/` — Timeline scrubber, Play/Pause, Speed
  - `ui/` — Reusable components (buttons, inputs, modals)

- **`lib/`**
  - `api.ts` — Axios client with SSE stream parser
  - `types.ts` — TypeScript interfaces for all data shapes
  - `translations.ts` — Jargon-free terminology (ecology → plain English)

#### UX Design

- **3-Step Wizard** — Non-expert path (species → region → simulate)
- **Pro Mode** — Advanced parameters for researchers
- **Live map** — Click to seed, see population heatmap in real-time
- **Charts** — Population trend, occupied area, invasion front velocity
- **Preset scenarios** — Curated historical examples

## Data Flow

### Simulation Workflow

```
User clicks "Run Simulation"
        ↓
Frontend sends SimulationConfig to /simulation/run
        ↓
Backend opens SSE stream to frontend
        ↓
For each step (n_steps):
  - sim.step() [NumPy vectorized]
  - Compute metrics
  - Emit SimulationProgress event
  - Frontend receives & renders
        ↓
All steps complete → Stream closes
        ↓
Frontend displays final result
```

### Species Niche Fitting

```
User searches for species, enters bbox
        ↓
GET /gbif/taxa/search → GBIF API
        ↓
User selects taxon
        ↓
POST /gbif/occurrences/thin → Fetch & thin to 10 km grid
        ↓
POST /gbif/niche/fit → Extract T,P at occurrence points
        ↓
Fit Gaussian: median = opt, quantile width = σ
        ↓
Return NicheParams → Frontend autocompletes
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **NumPy/SciPy core** | Performance (500+ steps/sec), reproducibility, testability |
| **Procedural climate fallback** | Works offline; no data download required to demo |
| **SSE streaming** | Real-time progress without polling; better UX |
| **Pydantic models** | Type safety, validation, OpenAPI schema generation |
| **Redis caching** | Fast repeat queries (GBIF, rasters), shared state |
| **Agent Skills + MCP** | Programmable via Claude/other LLMs; standardized tool export |
| **Separate API & frontend** | Independent versioning, scaling, testing |
| **Dark theme UI** | Ecological visualization; better for heatmaps |

## Performance Characteristics

- **Simulation speed**: 500–750 steps/sec (NumPy) on modern CPU, 104×236 grid
- **Grid resolution**: 0.25° (27.8 km at equator) default; 0.1° (11.1 km) for detailed analysis
- **GBIF queries**: ~2–5 sec (network latency), cached for 1 hour
- **Raster clipping**: <1 sec (single layer, <0.1 Gb)
- **Frontend render**: 60 FPS heatmap update (Deck.gl GPU acceleration)

## Testing Strategy

- **Unit tests** (`backend/tests/unit/`) — Model logic, kernel properties, mass conservation
- **Integration tests** (`backend/tests/integration/`) — API endpoints, GBIF fallback, raster loading
- **Frontend tests** — Component snapshots, SSE stream parsing (pending full implementation)

## Deployment Notes

### Local Development

```bash
make dev          # All services in foreground (Python + Node.js)
make up           # Docker Compose (production-like)
```

### Production (Docker)

```bash
docker-compose up -d
# API: http://localhost:8000
# Frontend: http://localhost:3000
# MCP: http://localhost:8001
```

### Environment Variables

See `backend/.env.example`. Key ones:

- `REDIS_URL` — Broker for Celery
- `GBIF_API_URL` — GBIF endpoint (hardcoded; override if needed)
- `CLIMATE_CACHE_DIR` — Where to cache rasters

### Database

No SQL database; all state in Redis + client-side. This keeps infrastructure minimal and suitable for serverless deployment.

## Future Extensions

1. **Climate change driver** — Time-varying temperature/precipitation layers
2. **Multi-species interactions** — Competitive/predator-prey dynamics
3. **Evolution** — Niche drift over generations
4. **Stage structure** — Age/size classes for complex life histories
5. **Spatial management** — Model human intervention (quarantine, translocation)
6. **Benchmarking suite** — Validate against published invasion models
7. **Serverless deployment** — AWS Lambda for simulation workers, S3 for rasters

## Code Structure Summary

```
backend/
├── app/
│   ├── main.py           # FastAPI factory
│   ├── core/             # Config, logging, Redis
│   ├── models/           # Pydantic schemas
│   ├── services/         # Business logic
│   ├── api/v1/           # REST endpoints
│   ├── workers/          # Celery tasks (scaffold)
│   └── sim_engine/       # Core NumPy/SciPy simulation
├── tests/
├── Dockerfile
└── pyproject.toml

frontend/
├── src/
│   ├── app/              # Next.js pages
│   ├── components/       # React components
│   ├── lib/              # API client, types
│   └── styles/           # Tailwind + custom CSS
├── package.json
└── Dockerfile

mcp_server/
├── server.py             # FastMCP tool definitions
└── Dockerfile

.skills/
├── fetch-gbif-occurrences/
├── process-climate-rasters/
├── run-spatial-simulation/
└── analyze-invasion-risk/

docker-compose.yml       # Full stack orchestration
Makefile                 # Development workflows
```

---

**Last updated**: 2026-08-16
**Status**: Production-ready scaffold with core services implemented
