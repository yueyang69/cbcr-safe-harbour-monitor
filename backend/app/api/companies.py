from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, require_roles
from ..models import Company
from ..schemas import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    company = Company(**payload.model_dump())
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@router.get("", response_model=list[CompanyRead])
async def list_companies(session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.REVIEWER, Role.ADMIN))):
    return list((await session.scalars(select(Company).order_by(Company.name))).all())
