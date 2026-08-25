from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, current_entity, require_roles
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
async def list_companies(session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.REVIEWER, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    query = select(Company).order_by(Company.name)
    if role == Role.SUBSIDIARY:
        if not entity_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Entity-Id header is required for subsidiary role")
        query = query.where(Company.id == entity_id)
    return list((await session.scalars(query)).all())
