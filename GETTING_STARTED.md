# Getting Started with BioSim-Engine

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 20+** (frontend)  
- **Redis** (broker & cache) — `brew install redis` (macOS) or `choco install redis` (Windows)
- **Docker + Docker Compose** (optional, for containerized setup)

### Option 1: Local Development (Recommended)

**Windows:**
```powershell
# Install dependencies
cd backend
pip install -r requirements.txt

cd ../frontend
npm install

# Go back to root
cd ..

# Copy environment configuration
copy backend\.env.example backend\.env

# Start services manually (3 separate PowerShell windows):

# Terminal 1: Redis
redis-server

# Terminal 2: FastAPI
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 3: Next.js
cd frontend
npm run dev
```

**macOS:**
```bash
# Install prerequisites (skip anything you already have)
brew install python@3.11 node@20 redis gdal

# Install dependencies (uses pip3 — macOS doesn't ship a bare `pip`)
make install
make env-setup

# Start Redis as a background service
brew services start redis

make dev
```

See [QUICK_START_MACOS.md](QUICK_START_MACOS.md) for a step-by-step walkthrough
and troubleshooting.

**Linux:**
```bash
make install
make env-setup
make dev
```

Then open:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Option 2: Docker Compose (Production-like)

```bash
make up
```

Same URLs apply; services auto-start and log output goes to console.

---

## Your First Simulation

### 1. **Frontend**

1. Navigate to http://localhost:3000
2. Click **"Run Demo Simulation"** in the sidebar
   - This uses a pre-configured oak tree in the contiguous USA
3. Watch the invasion heatmap in real-time
4. Scrub the timeline at the bottom to explore different time steps

### 2. **API Directly** (curl)

```bash
# Search for a species
curl -s http://localhost:8000/api/v1/gbif/taxa/search?query=Quercus%20alba | jq .

# List available climate layers
curl -s http://localhost:8000/api/v1/rasters/layers | jq .

# Run simulation (streaming)
curl -s -X POST http://localhost:8000/api/v1/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "region": "demo",
    "species_name": "Oak",
    "bbox": [-125, 25, -66, 49],
    "resolution_deg": 0.25,
    "temperature_opt": 15,
    "temperature_sigma": 8,
    "precipitation_opt": 900,
    "precipitation_sigma": 300,
    "niche_floor": 0.1,
    "carrying_capacity": 1000,
    "demography": {"r": 0.1, "m": 0.05},
    "dispersal": {
      "kernel_type": "gaussian",
      "sigma": 10,
      "fraction": 0.1
    },
    "n_steps": 50
  }'
```

### 3. **AI Agent (MCP)**

If you're using Claude Code or another MCP-compatible client:

```bash
# Start MCP server
cd mcp_server
python -m server

# Now use Claude with BioSim tools:
# - search_species(query)
# - fetch_occurrences(species_key, bbox)
# - run_simulation(...)
# - analyze_invasion_risk(...)
```

---

## Project Structure

### Backend

```
backend/
├── app/
│   ├── main.py               # FastAPI app factory
│   ├── core/
│   │   ├── config.py         # Pydantic Settings
│   │   ├── logging.py        # Structured JSON logging
│   │   └── redis.py          # Async Redis client
│   ├── models/               # Request/response schemas
│   ├── services/             # Business logic
│   │   ├── gbif_service.py
│   │   ├── climate_service.py
│   │   └── simulation_service.py
│   ├── api/v1/endpoints/     # REST endpoints
│   │   ├── gbif.py
│   │   ├── rasters.py
│   │   └── simulation.py
│   ├── workers/              # Celery tasks (scaffold)
│   └── sim_engine/           # Core NumPy/SciPy simulation
│       ├── model.py          # Reaction-diffusion model
│       ├── data.py           # Data loading & processing
│       └── species.py        # Parameter presets
├── tests/                    # Unit & integration tests
├── pyproject.toml            # Dependencies
└── Dockerfile
```

### Frontend

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx        # Root layout
│   │   └── page.tsx          # Master dashboard
│   ├── components/
│   │   ├── map/              # MapLibre + Deck.gl
│   │   ├── panels/           # Sidebar, analytics
│   │   ├── hud/              # Timeline, controls
│   │   └── ui/               # Reusable components
│   ├── lib/
│   │   ├── api.ts            # Axios + SSE client
│   │   ├── types.ts          # TypeScript interfaces
│   │   └── translations.ts   # Jargon-free UI text
│   └── styles/               # Tailwind + globals
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── next.config.js
└── Dockerfile
```

### Agent Skills

```
.skills/
├── fetch-gbif-occurrences/   # Get species records
├── process-climate-rasters/  # Clip climate data
├── run-spatial-simulation/   # Execute model
└── analyze-invasion-risk/    # Compute metrics
```

---

## Common Tasks

### Running Tests

```bash
make test              # All tests
make test-backend      # Backend only (pytest)
```

### Code Quality

```bash
make lint              # Check code style
make fmt               # Auto-format (black, prettier)
```

### View Logs

```bash
make logs              # All services (Docker)
make logs-api          # API only
docker-compose logs -f worker  # Celery worker
```

### Stop Services

```bash
make down              # Docker
Ctrl+C                 # Local development
```

---

## Configuration

### Backend Environment (`.env`)

```ini
# Defaults in backend/.env.example
DEBUG=true
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
GBIF_API_URL=https://api.gbif.org/v1
```

### Frontend Environment

Set `NEXT_PUBLIC_API_URL` to point to your API:

```bash
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Adding Real Climate Data

By default, BioSim-Engine uses **procedural climate** (synthetic gradients) so you can run it immediately without downloads.

To use **real climate data** (WorldClim, GEBCO, etc.):

1. Download GeoTIFF files to `data/climate/`:
   ```bash
   # Example: WorldClim v2.1 10-minute resolution
   wget https://biogeo.ucdavis.edu/data/worldclim/v2.1/aggregated/wc2.1_10m_bio_1.tif
   mv wc2.1_10m_bio_1.tif data/climate/temperature.tif
   ```

2. Climate layers appear automatically in the API:
   ```bash
   curl http://localhost:8000/api/v1/rasters/layers
   ```

3. Simulation will use real data when available, fall back to procedural if not.

---

## Key Endpoints

### GBIF Integration

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/gbif/taxa/search` | Search species by name |
| `POST` | `/api/v1/gbif/occurrences/search` | Fetch occurrence records |
| `POST` | `/api/v1/gbif/occurrences/thin` | Fetch + spatial thin records |
| `POST` | `/api/v1/gbif/niche/fit` | Fit niche envelope from occurrences |

### Climate Data

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/rasters/layers` | List available layers |
| `POST` | `/api/v1/rasters/clip` | Clip layer to bbox |

### Simulation

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/simulation/run` | Run simulation (SSE stream) |
| `POST` | `/api/v1/simulation/estimate` | Estimate runtime |
| `GET` | `/api/v1/simulation/presets` | List preset scenarios |

### Health

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/health` | Service status |

**Full OpenAPI docs**: http://localhost:8000/docs (when running)

---

## Troubleshooting

### "Connection refused" on Redis

```bash
# Start Redis manually
redis-server

# Or in Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

### Frontend can't reach API

Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`:

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

### Rasterio import error

```bash
# Install GDAL (macOS)
brew install gdal

# Linux (Ubuntu/Debian)
sudo apt-get install gdal-bin libgdal-dev

# Then reinstall Python dependencies
cd backend
pip install --no-cache-dir -e ".[dev]"
```

### Slow simulation startup

First run caches procedural climate. Subsequent runs are instant. If you're using real rasters, the first clipping is slower (~1–2 sec).

---

## Next Steps

1. **Read [ARCHITECTURE.md](ARCHITECTURE.md)** — Deep dive into design decisions
2. **Explore API docs** — http://localhost:8000/docs
3. **Try Agent Skills** — Use MCP server with Claude Code
4. **Add real data** — Download climate layers for your region
5. **Extend the model** — Add stage structure, climate change, evolution
6. **Deploy** — Use Docker to production (cloud provider of choice)

---

## Support

- **Simulation questions?** See comments in `backend/app/sim_engine/model.py`
- **API issues?** Check logs with `make logs-api`
- **Frontend bugs?** Open browser DevTools (F12) → Console
- **MCP setup?** See `mcp_server/server.py`

---

## License

This project is provided as-is for educational and research use.

**Last updated**: 2026-08-16
