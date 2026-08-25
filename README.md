# CbCR Safe Harbour Monitor

Transitional CbCR Safe Harbour automated testing and risk-warning MVP.

This application evaluates De minimis, Simplified ETR, and Routine Profits tests by jurisdiction and fiscal year. It is a risk-warning tool only and does not calculate GloBE Top-up Tax.

## Stack

- Backend: Python 3.11+, FastAPI, async SQLAlchemy, PostgreSQL, Alembic
- Frontend: React 18, TypeScript, Vite, React Router, Tailwind CSS
- Tests: pytest and Vitest
- AI: MiniMax LLM API integration

## Quick Start with Docker Compose

```powershell
# 1. Build and start all services (DB + API + Web)
docker compose up --build

# 2. In a new terminal, run database migrations
docker compose exec api alembic upgrade head

# 3. Seed initial company data
docker compose exec api python seed.py

# 4. Open the application
# Web app: http://localhost:5173
# API docs: http://localhost:8000/docs
```

## Manual Setup (Without Docker)

### Backend

```powershell
cd backend

# Install dependencies
pip install -e .

# Set up database (PostgreSQL must be running)
$env:DATABASE_URL = "postgresql+asyncpg://cbcr:cbcr_dev_only@localhost:5432/cbcr"
alembic upgrade head

# Seed initial data
python seed.py

# Start API server
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend

# Install dependencies
npm install

# Set API URL (optional, defaults to localhost:8000)
$env:VITE_API_BASE_URL = "http://localhost:8000/api/v1"

# Start dev server
npm run dev
```

## Run tests locally

Frontend:

```powershell
cd frontend
npm install
npm run test -- --run
npm run build
```

Backend:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests -q
```

## Environment Variables

### Backend (.env file)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://cbcr:cbcr_dev_only@localhost:5432/cbcr

# CORS
CORS_ORIGINS=http://localhost:5173,http://47.253.231.221:5173

# AI Service (V2.0)
MINIMAX_API_KEY=<your-minimax-api-key>
MINIMAX_API_BASE=https://api.minimaxi.com/v1  # Optional
```

### Frontend (.env file)

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Roles

Set the `X-User-Role` request header to `subsidiary`, `hq`, or `reviewer`. `admin` is available for local development.

All calculations are performed by the backend using deterministic rules. Missing data and non-EUR data require manual confirmation; no currency conversion is performed.

## V2.0 AI Features

- **Smart Field Mapping**: AI-enhanced mapping with 60+ Chinese/English field dictionary
- **Anomaly Detection**: Detects ratio issues, volatility, and missing critical fields
- **Missing Value Suggestions**: Suggests values based on historical data median
- **Risk Briefing Generator**: Auto-generates 200-character Chinese risk summaries
- **Tax Q&A Assistant**: Chat-based assistant for explaining calculated values (strict scope limitation)

**Important**: All AI outputs require human confirmation. AI never participates in core Safe Harbour calculations.

## Initial Data

After running `seed.py`, the following sample companies will be available:
- Acme Japan KK (Japan)
- Acme Netherlands BV (Netherlands)
- Acme Germany GmbH (Germany)
- Acme UK Ltd (United Kingdom)
- Acme Singapore Pte Ltd (Singapore)

## Troubleshooting

### Company dropdown is empty
Run the seed script: `python backend/seed.py` or `docker compose exec api python seed.py`

### AI features not working
Check that `MINIMAX_API_KEY` is set in backend environment. AI will gracefully degrade to mock responses if unavailable.

### Database connection errors
Ensure PostgreSQL is running and `DATABASE_URL` is correctly configured.
