from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, require_roles
from ..models import JurisdictionSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(fiscal_year: int | None = None, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.REVIEWER, Role.ADMIN))):
    query = select(JurisdictionSummary)
    if fiscal_year is not None:
        query = query.where(JurisdictionSummary.fiscal_year == fiscal_year)
    rows = list((await session.scalars(query)).all())
    return {
        "fiscal_year": fiscal_year,
        "kpis": {
            "jurisdiction_count": len(rows),
            "pass_count": sum(row.status == "PASS" for row in rows),
            "warning_count": sum(row.status == "WARNING" for row in rows),
            "incomplete_count": sum(row.status == "INCOMPLETE" for row in rows),
        },
        "jurisdictions": [
            {"id": row.id, "jurisdiction": row.jurisdiction, "revenue": row.revenue, "pbt": row.pbt,
             "evaluation": row.evaluation, "status": row.status, "warnings": row.warnings}
            for row in rows
        ],
    }
