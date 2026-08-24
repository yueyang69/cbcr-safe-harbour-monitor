from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, require_roles
from ..models import JurisdictionSummary
from ..services.aggregation import rebuild_summaries

router = APIRouter(prefix="/summaries", tags=["summaries"])


def summary_payload(summary: JurisdictionSummary) -> dict:
    return {
        "id": summary.id, "jurisdiction": summary.jurisdiction, "fiscal_year": summary.fiscal_year,
        "revenue": summary.revenue, "pbt": summary.pbt, "covered_taxes": summary.covered_taxes,
        "payroll": summary.payroll, "tangible_assets": summary.tangible_assets,
        "company_count": summary.company_count, "included_count": summary.included_count,
        "status": summary.status, "evaluation": summary.evaluation, "warnings": summary.warnings,
    }


@router.post("/rebuild")
async def rebuild(fiscal_year: int | None = None, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    summaries = await rebuild_summaries(session, fiscal_year)
    return [summary_payload(summary) for summary in summaries]


@router.get("")
async def list_summaries(fiscal_year: int | None = None, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.REVIEWER, Role.ADMIN))):
    query = select(JurisdictionSummary).order_by(JurisdictionSummary.jurisdiction)
    if fiscal_year is not None:
        query = query.where(JurisdictionSummary.fiscal_year == fiscal_year)
    return [summary_payload(summary) for summary in (await session.scalars(query)).all()]


@router.get("/{summary_id}")
async def get_summary(summary_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.REVIEWER, Role.ADMIN))):
    summary = await session.get(JurisdictionSummary, summary_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary_payload(summary)
