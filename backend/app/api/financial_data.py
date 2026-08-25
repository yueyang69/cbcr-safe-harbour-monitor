from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, current_entity, require_entity_scope, require_roles
from ..models import Company, FinancialData
from ..schemas import FinancialDataCreate, FinancialDataRead, ReturnRequest
from ..services.aggregation import rebuild_summaries

router = APIRouter(prefix="/financial-data", tags=["financial-data"])


async def get_company(session: AsyncSession, company_id: str) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


async def get_financial_data(session: AsyncSession, data_id: str) -> FinancialData:
    data = await session.get(FinancialData, data_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Financial data not found")
    return data


@router.post("", response_model=FinancialDataRead, status_code=status.HTTP_201_CREATED)
async def create_financial_data(payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    # Scope check before the 404 lookup so a subsidiary cannot probe whether another entity exists.
    require_entity_scope(role, entity_id, payload.company_id)
    await get_company(session, payload.company_id)
    existing = await session.scalar(select(FinancialData).where(FinancialData.company_id == payload.company_id, FinancialData.fiscal_year == payload.fiscal_year))
    if existing:
        raise HTTPException(status_code=409, detail="Financial data already exists for company and year")
    data = FinancialData(**payload.model_dump(), requires_manual_confirmation=payload.currency != "EUR")
    session.add(data)
    await session.commit()
    await session.refresh(data)
    return data


@router.post("/quick-submit", response_model=FinancialDataRead)
async def quick_submit_financial_data(payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    """MVP quick-test loop: upsert source data, auto-approve it, and rebuild
    jurisdiction summaries so it shows up on the Dashboard immediately.

    HQ/admin only — the approver enters and approves in one step. A subsidiary
    still follows the strict submit -> HQ approve flow and never sees the
    Dashboard (permission matrix unchanged).
    """
    await get_company(session, payload.company_id)
    data = await session.scalar(select(FinancialData).where(
        FinancialData.company_id == payload.company_id,
        FinancialData.fiscal_year == payload.fiscal_year,
    ))
    if data is None:
        data = FinancialData(**payload.model_dump(), requires_manual_confirmation=payload.currency != "EUR")
        session.add(data)
    else:
        for field, value in payload.model_dump().items():
            setattr(data, field, value)
        data.requires_manual_confirmation = payload.currency != "EUR"
    data.is_submitted = True
    data.is_approved = True
    data.return_reason = None
    await session.commit()
    await rebuild_summaries(session, payload.fiscal_year)
    await session.refresh(data)
    return data


@router.get("", response_model=list[FinancialDataRead])
async def list_financial_data(company_id: str | None = None, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.REVIEWER, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    query = select(FinancialData).order_by(FinancialData.fiscal_year.desc())
    if role == Role.SUBSIDIARY:
        if not entity_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Entity-Id header is required for subsidiary role")
        if company_id and company_id != entity_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subsidiary role is restricted to its own entity")
        query = query.where(FinancialData.company_id == entity_id)
    elif company_id:
        query = query.where(FinancialData.company_id == company_id)
    return list((await session.scalars(query)).all())


@router.post("/{data_id}/submit", response_model=FinancialDataRead)
async def submit_financial_data(data_id: str, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    data = await get_financial_data(session, data_id)
    require_entity_scope(role, entity_id, data.company_id)
    data.is_submitted = True
    # A resubmission is a fresh review cycle — drop the previous return reason.
    data.return_reason = None
    await session.commit()
    await session.refresh(data)
    return data


@router.post("/{data_id}/approve", response_model=FinancialDataRead)
async def approve_financial_data(data_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    data = await get_financial_data(session, data_id)
    data.is_approved = True
    await session.commit()
    # Strict flow: approval is what publishes to the Dashboard, so rebuild the
    # jurisdiction cache immediately (quick-submit already does this in one step).
    await rebuild_summaries(session, data.fiscal_year)
    await session.refresh(data)
    return data


@router.post("/{data_id}/return", response_model=FinancialDataRead)
async def return_financial_data(data_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN)), return_request: ReturnRequest | None = Body(default=None)):
    """HQ returns submitted data so the reporting entity can edit it again.

    An optional `reason` is attached so the subsidiary knows why it was sent back.
    """
    data = await get_financial_data(session, data_id)
    data.is_submitted = False
    data.is_approved = False
    data.return_reason = return_request.reason if return_request else None
    await session.commit()
    # A returned jurisdiction must leave the Dashboard until it is re-approved.
    await rebuild_summaries(session, data.fiscal_year)
    await session.refresh(data)
    return data


@router.put("/{data_id}", response_model=FinancialDataRead)
async def update_financial_data(data_id: str, payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    data = await get_financial_data(session, data_id)
    require_entity_scope(role, entity_id, data.company_id)
    require_entity_scope(role, entity_id, payload.company_id)
    if role == Role.SUBSIDIARY and data.is_submitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submitted data must be returned by HQ before editing")
    await get_company(session, payload.company_id)
    existing = await session.scalar(select(FinancialData).where(
        FinancialData.company_id == payload.company_id,
        FinancialData.fiscal_year == payload.fiscal_year,
        FinancialData.id != data_id,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="Financial data already exists for company and year")
    for field, value in payload.model_dump().items():
        setattr(data, field, value)
    data.requires_manual_confirmation = payload.currency != "EUR"
    await session.commit()
    await session.refresh(data)
    return data


@router.delete("/{data_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_data(data_id: str, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    data = await get_financial_data(session, data_id)
    require_entity_scope(role, entity_id, data.company_id)
    if role == Role.SUBSIDIARY and data.is_submitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submitted data must be returned by HQ before deletion")
    fiscal_year = data.fiscal_year
    await session.delete(data)
    await session.commit()
    # Removing an approved row must drop it from the Dashboard cache.
    await rebuild_summaries(session, fiscal_year)
