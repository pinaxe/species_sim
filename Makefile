.PHONY: help install dev prod up down logs clean test lint fmt

help:
	@echo "BioSim-Engine Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install all dependencies"
	@echo "  make env-setup    - Copy .env.example to .env"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Run all services locally (requires Python 3.11+, Node.js 20+)"
	@echo "  make dev-api      - Run FastAPI dev server only"
	@echo "  make dev-frontend - Run Next.js dev server only"
	@echo ""
	@echo "Docker:"
	@echo "  make up           - Start all services with Docker Compose"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - View logs from all services"
	@echo "  make logs-api     - View logs from API service"
	@echo ""
	@echo "Quality:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests"
	@echo "  make lint         - Run linting checks"
	@echo "  make fmt          - Format code (black, prettier)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove build artifacts and cache"

install:
	@echo "Installing backend dependencies..."
	cd backend && pip3 install -r requirements.txt --no-cache-dir
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ All dependencies installed"

env-setup:
	cp backend/.env.example backend/.env
	@echo "✓ Created backend/.env (edit as needed)"

dev: env-setup
	@echo "Starting BioSim-Engine in development mode..."
	@echo "API: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Start Redis:"
	redis-server --daemonize yes
	@echo "Start FastAPI:"
	cd backend && uvicorn app.main:app --reload --port 8000 &
	@echo "Start Next.js:"
	cd frontend && npm run dev &
	@echo ""
	@echo "Press Ctrl+C to stop all services"
	wait

dev-api: env-setup
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

test: test-backend
	@echo "✓ All tests passed"

test-backend:
	cd backend && pytest -v --cov=app tests/

lint:
	@echo "Linting Python..."
	cd backend && ruff check app
	@echo "Type checking Python..."
	cd backend && mypy app
	@echo "Linting TypeScript..."
	cd frontend && npm run lint

fmt:
	@echo "Formatting Python..."
	cd backend && black app tests
	cd backend && ruff check --fix app
	@echo "Formatting TypeScript..."
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,json}"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/.next frontend/out
	rm -rf .DS_Store
	@echo "✓ Cleaned up build artifacts"

build-docker:
	docker-compose build

docs:
	@echo "API Documentation: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"
