from fastapi import APIRouter, Depends
from sqlalchemy import select
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
    _: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN))
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
    role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN))
):
    """Confirm AI-suggested mappings after human review.

    HQ/admin confirm persists a GLOBAL mapping rule — the shared dictionary the
    whole group uses. A subsidiary's confirm is scoped to THIS entity/upload
    only: it acknowledges the mapping used for its own data and must never
    modify the global rules. (Per-entity mapping_rule can be added later if
    multinational entity tables diverge.)
    """
    if role in (Role.HQ, Role.ADMIN):
        for mapping in payload.mappings:
            # Idempotent upsert: re-confirming a known rule updates it instead of
            # tripping the (source_field, target_field) unique constraint.
            rule = await session.scalar(select(MappingRule).where(
                MappingRule.source_field == mapping.source_field,
                MappingRule.target_field == mapping.target_field,
            ))
            if rule is None:
                session.add(MappingRule(
                    source_field=mapping.source_field,
                    target_field=mapping.target_field,
                    confirmed_by=role.value,
                    confidence_score=float(mapping.confidence),
                    confirmed_by_user=True,  # Human confirmed after AI suggestion
                ))
            else:
                rule.confirmed_by = role.value
                rule.confidence_score = float(mapping.confidence)
                rule.confirmed_by_user = True
        await session.commit()
    return payload.mappings
