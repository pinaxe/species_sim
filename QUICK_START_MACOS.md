# Quick Start - macOS

Get BioSim-Engine running on macOS in 5 minutes.

## Prerequisites

Install [Homebrew](https://brew.sh) first if you don't have it, then:

```bash
# Python 3.11+, Node.js 20+, Redis, and GDAL (needed by rasterio/geopandas)
brew install python@3.11 node@20 redis gdal

# Verify
python3 --version   # Should be 3.11+
node --version       # Should be 20+
npm --version
pip3 --version       # macOS ships pip3, not a bare `pip` — use pip3 throughout
```

## Install Dependencies

Open Terminal in the project root:

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..

echo "✓ Dependencies installed"
```

Keep the backend virtualenv activated (`source backend/.venv/bin/activate`) in
any terminal window where you run `uvicorn`, `pytest`, or `make dev-api`.

## Start Services (3 Terminal Tabs/Windows)

### Tab 1: Redis

```bash
brew services start redis
# or run it in the foreground instead:
redis-server
```

### Tab 2: FastAPI Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Wait for: `Uvicorn running on http://127.0.0.1:8000`

### Tab 3: Next.js Frontend

```bash
cd frontend
npm run dev
```

Wait for: `ready - started server on 0.0.0.0:3000, url: http://localhost:3000`

## Open in Browser

- **App**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

## Try the Demo

1. Click **"Run Demo Simulation"** in the sidebar
2. Watch the invasion heatmap in real-time
3. Scrub the timeline at the bottom

## Troubleshooting

### Redis not starting

```bash
brew services list          # check status
brew services restart redis
redis-cli ping               # should return: PONG
```

### `rasterio` / `geopandas` fail to build

These need GDAL, which isn't always picked up automatically on macOS:

```bash
brew install gdal
cd backend
pip3 install --no-cache-dir -r requirements.txt
```

On Apple Silicon, if the build still can't find GDAL headers, point pip at
Homebrew's install:

```bash
export GDAL_CONFIG=$(brew --prefix gdal)/bin/gdal-config
pip3 install --no-cache-dir -r requirements.txt
```

### Frontend can't reach API

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then restart: `npm run dev`

### "ModuleNotFoundError: No module named 'fastapi'"

```bash
cd backend
source .venv/bin/activate
pip3 install -r requirements.txt
```

### Port 8000 already in use

```bash
# Find what's using port 8000
lsof -i :8000

# Or use a different port
uvicorn app.main:app --reload --port 8001
# Then update frontend .env.local with port 8001
```

## Environment Configuration

Create `backend/.env` (copy from `.env.example`):

```bash
cp backend/.env.example backend/.env
```

```ini
DEBUG=true
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
GBIF_API_URL=https://api.gbif.org/v1
```

## Next Steps

- Read **[GETTING_STARTED.md](GETTING_STARTED.md)** for full guide
- Read **[ARCHITECTURE.md](ARCHITECTURE.md)** for design deep-dive
- Explore **http://localhost:8000/docs** (API OpenAPI spec)

---

**Still having issues?** Check that all three processes are running:
- Redis: `redis-cli ping` → PONG
- Backend: http://localhost:8000/health → `{"status":"healthy"}`
- Frontend: http://localhost:3000 → loads page
