from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, require_roles
from ..schemas import MappingConfirmRequest, MappingSuggestion, MappingSuggestRequest
from ..models import MappingRule
from ..services.ai_service import AIService

router = APIRouter(prefix="/mapping", tags=["mapping"])


@router.post("/suggest", response_model=list[MappingSuggestion])
async def suggest_mapping(
    payload: MappingSuggestRequest,
    session: AsyncSession = Depends(get_session),
    _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))
):
    """AI-enhanced field mapping with comprehensive fallback dictionary.

    Returns Top 3 candidates with confidence scores.
    Confidence < 60% forces manual selection on frontend.
    """
    ai_service = AIService(session)
    suggestions_data = await ai_service.suggest_field_mapping(payload.source_fields)

    return [
        MappingSuggestion(
            source_field=s["source_field"],
            target_field=s["target_field"],
            confidence=s["confidence"]
        )
        for s in suggestions_data
    ]


@router.post("/confirm", response_model=list[MappingSuggestion])
async def confirm_mapping(
    payload: MappingConfirmRequest,
    session: AsyncSession = Depends(get_session),
    _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))
):
    """Confirm AI-suggested mappings after human review.

    All mappings marked as confirmed_by_user=True after manual approval.
    """
    for mapping in payload.mappings:
        session.add(MappingRule(
            source_field=mapping.source_field,
            target_field=mapping.target_field,
            confirmed_by="hq",
            confidence_score=float(mapping.confidence),
            confirmed_by_user=True,  # Human confirmed after AI suggestion
        ))
    await session.commit()
    return payload.mappings
