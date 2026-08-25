"""Static list of recognised jurisdictions for the data-entry datalist."""
from fastapi import APIRouter
from ..jurisdictions import CANONICAL_JURISDICTIONS

router = APIRouter(prefix="/jurisdictions", tags=["jurisdictions"])


@router.get("")
async def list_jurisdictions() -> dict[str, list[str]]:
    """Canonical country/region names, sorted for the frontend picker."""
    return {"jurisdictions": sorted(CANONICAL_JURISDICTIONS)}
