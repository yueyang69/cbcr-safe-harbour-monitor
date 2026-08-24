from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, require_roles
from ..schemas import MappingConfirmRequest, MappingSuggestion, MappingSuggestRequest
from ..models import MappingRule

router = APIRouter(prefix="/mapping", tags=["mapping"])

ALIASES = {
    "jurisdiction": "jurisdiction", "辖区": "jurisdiction", "country": "jurisdiction",
    "fiscal year": "fiscal_year", "年度": "fiscal_year", "year": "fiscal_year",
    "cbcr revenue": "revenue", "revenue": "revenue", "收入": "revenue",
    "cbcr pbt": "pbt", "pbt": "pbt", "利润": "pbt", "税前利润": "pbt",
    "simplified covered taxes": "covered_taxes", "covered taxes": "covered_taxes", "税费": "covered_taxes",
    "eligible payroll costs": "payroll", "payroll": "payroll", "工资": "payroll",
    "eligible tangible assets": "tangible_assets", "tangible assets": "tangible_assets", "有形资产": "tangible_assets",
    "currency": "currency", "币种": "currency",
}


@router.post("/suggest", response_model=list[MappingSuggestion])
async def suggest_mapping(payload: MappingSuggestRequest, _: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN))):
    suggestions = []
    for source in payload.source_fields:
        target = ALIASES.get(source.strip().lower())
        if target:
            suggestions.append(MappingSuggestion(source_field=source, target_field=target, confidence="0.98"))
    return suggestions


@router.post("/confirm", response_model=list[MappingSuggestion])
async def confirm_mapping(payload: MappingConfirmRequest, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    for mapping in payload.mappings:
        session.add(MappingRule(source_field=mapping.source_field, target_field=mapping.target_field, confirmed_by="hq"))
    await session.commit()
    return payload.mappings
