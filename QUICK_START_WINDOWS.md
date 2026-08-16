# Quick Start - Windows

Get BioSim-Engine running on Windows in 5 minutes.

## Prerequisites

```powershell
# Install Redis (using Chocolatey)
choco install redis

# Or use Docker instead
docker run -d -p 6379:6379 redis:7-alpine

# Verify Python and Node.js
python --version  # Should be 3.11+
node --version    # Should be 20+
npm --version
```

## Install Dependencies

Open PowerShell in the project root:

```powershell
# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend  
cd frontend
npm install
cd ..

echo "✓ Dependencies installed"
```

## Start Services (3 PowerShell Windows)

### Window 1: Redis

```powershell
redis-server
```

Or if using Docker:
```powershell
docker run -p 6379:6379 redis:7-alpine
```

### Window 2: FastAPI Backend

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

Wait for: `Uvicorn running on http://127.0.0.1:8000`

### Window 3: Next.js Frontend

```powershell
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
```powershell
# Install Redis via Chocolatey
choco install redis

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine

# Verify connection
redis-cli ping
# Should return: PONG
```

### Frontend can't reach API
Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then restart: `npm run dev`

### "ModuleNotFoundError: No module named 'fastapi'"
```powershell
cd backend
pip install -r requirements.txt
```

### Port 8000 already in use
```powershell
# Find what's using port 8000
Get-Process | Where-Object { $_.Handles -like "*8000*" }

# Or use a different port
uvicorn app.main:app --reload --port 8001
# Then update frontend .env.local with port 8001
```

## Environment Configuration

Create `backend\.env` (copy from `.env.example`):

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
