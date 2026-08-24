# CbCR Safe Harbour Monitor

Transitional CbCR Safe Harbour automated testing and risk-warning MVP.

This application evaluates De minimis, Simplified ETR, and Routine Profits tests by jurisdiction and fiscal year. It is a risk-warning tool only and does not calculate GloBE Top-up Tax.

## Stack

- Backend: Python 3.11+, FastAPI, async SQLAlchemy, PostgreSQL, Alembic
- Frontend: React 18, TypeScript, Vite, React Router, Tailwind CSS
- Tests: pytest and Vitest

## Run with Docker Compose

```powershell
docker compose up --build
```

Open `http://localhost:5173` for the web app and `http://localhost:8000/docs` for the API documentation.

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

## Roles

Set the `X-User-Role` request header to `subsidiary`, `hq`, or `reviewer`. `admin` is available for local development.

All calculations are performed by the backend using deterministic rules. Missing data and non-EUR data require manual confirmation; no currency conversion is performed.
