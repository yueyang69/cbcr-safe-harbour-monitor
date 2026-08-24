from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, require_roles
from ..models import Company, FinancialData
from ..schemas import FinancialDataCreate, FinancialDataRead

router = APIRouter(prefix="/financial-data", tags=["financial-data"])


async def get_company(session: AsyncSession, company_id: str) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("", response_model=FinancialDataRead, status_code=status.HTTP_201_CREATED)
async def create_financial_data(payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN))):
    await get_company(session, payload.company_id)
    existing = await session.scalar(select(FinancialData).where(FinancialData.company_id == payload.company_id, FinancialData.fiscal_year == payload.fiscal_year))
    if existing:
        raise HTTPException(status_code=409, detail="Financial data already exists for company and year")
    data = FinancialData(**payload.model_dump(), requires_manual_confirmation=payload.currency != "EUR")
    session.add(data)
    await session.commit()
    await session.refresh(data)
    return data


@router.get("", response_model=list[FinancialDataRead])
async def list_financial_data(company_id: str | None = None, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.REVIEWER, Role.ADMIN))):
    query = select(FinancialData).order_by(FinancialData.fiscal_year.desc())
    if company_id:
        query = query.where(FinancialData.company_id == company_id)
    return list((await session.scalars(query)).all())


@router.post("/{data_id}/submit", response_model=FinancialDataRead)
async def submit_financial_data(data_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN))):
    data = await session.get(FinancialData, data_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Financial data not found")
    data.is_submitted = True
    await session.commit()
    await session.refresh(data)
    return data


@router.post("/{data_id}/approve", response_model=FinancialDataRead)
async def approve_financial_data(data_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    data = await session.get(FinancialData, data_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Financial data not found")
    data.is_approved = True
    await session.commit()
    await session.refresh(data)
    return data
