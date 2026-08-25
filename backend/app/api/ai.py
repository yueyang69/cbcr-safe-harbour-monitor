"""AI-powered endpoints for anomaly detection, missing value suggestions, and risk briefing."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import Role, current_entity, require_entity_scope, require_roles
from ..schemas import (
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    BriefingResponse,
    ChatRequest,
    ChatResponse,
    SuggestMissingRequest,
    SuggestMissingResponse,
)
from ..services.ai_service import AIService, AIServiceError

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/anomaly-detection", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    payload: AnomalyDetectionRequest,
    session: AsyncSession = Depends(get_session),
    role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)),
    entity_id: str | None = Depends(current_entity),
):
    """Detect data anomalies: ratio issues, volatility vs prior year, missing critical fields.

    WARNING ONLY - never auto-modifies values.
    """
    require_entity_scope(role, entity_id, payload.company_id)
    try:
        ai_service = AIService(session)
        anomalies = await ai_service.detect_anomalies(
            company_id=payload.company_id,
            fiscal_year=payload.fiscal_year,
            jurisdiction=payload.jurisdiction,
            revenue=payload.revenue,
            pbt=payload.pbt,
            covered_taxes=payload.covered_taxes,
            payroll=payload.payroll,
            tangible_assets=payload.tangible_assets,
        )

        return AnomalyDetectionResponse(anomalies=anomalies)

    except AIServiceError as error:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {error}") from error


@router.post("/suggest-missing", response_model=SuggestMissingResponse)
async def suggest_missing_value(
    payload: SuggestMissingRequest,
    session: AsyncSession = Depends(get_session),
    role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)),
    entity_id: str | None = Depends(current_entity),
):
    """Suggest missing field value based on company historical data (median/average).

    Requires user confirmation before applying.
    """
    require_entity_scope(role, entity_id, payload.company_id)
    try:
        ai_service = AIService(session)
        suggestion = await ai_service.suggest_missing_value(
            company_id=payload.company_id,
            field_name=payload.field_name,
        )

        return SuggestMissingResponse(**suggestion)

    except AIServiceError as error:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {error}") from error


@router.post("/briefing", response_model=BriefingResponse)
async def generate_briefing(
    fiscal_year: int | None = None,
    session: AsyncSession = Depends(get_session),
    _: Role = Depends(require_roles(Role.HQ, Role.REVIEWER, Role.ADMIN)),
):
    """Generate AI-powered risk briefing (max 200 Chinese characters).

    Summarizes high-risk jurisdictions, ETR gaps, and priority recommendations.

    DISCLAIMER: AI-generated summary for reference only, not tax advice.
    """
    try:
        ai_service = AIService(session)
        briefing = await ai_service.generate_risk_briefing(fiscal_year=fiscal_year)

        return BriefingResponse(**briefing)

    except AIServiceError as error:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {error}") from error


@router.post("/chat", response_model=ChatResponse)
async def chat_assistant(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
    _: Role = Depends(require_roles(Role.HQ, Role.REVIEWER, Role.ADMIN)),
):
    """Tax data Q&A assistant with strict scope limitation.

    Only explains existing computed values (PBT, ETR, SBIE, De minimis).
    FORBIDDEN: tax calculation advice, avoidance strategies, legal opinions.
    """
    try:
        ai_service = AIService(session)
        response = await ai_service.chat_assistant(
            message=payload.message,
            jurisdiction=payload.jurisdiction,
        )

        return ChatResponse(**response)

    except AIServiceError as error:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {error}") from error
