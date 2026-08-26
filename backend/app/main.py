from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import ai, auth, companies, dashboard, financial_data, health, jurisdictions, mappings, summaries
from .config import get_settings

app = FastAPI(title="Transitional CbCR Safe Harbour Risk Warning API", version="0.1.0")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(jurisdictions.router, prefix="/api/v1")
app.include_router(financial_data.router, prefix="/api/v1")
app.include_router(mappings.router, prefix="/api/v1")
app.include_router(summaries.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
