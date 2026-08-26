from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..jurisdictions import CANONICAL_JURISDICTIONS, normalize_jurisdiction


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    entity_type: Literal["subsidiary", "branch"] = "subsidiary"
    parent_entity_id: str | None = None


class CompanyRead(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class FinancialDataCreate(BaseModel):
    company_id: str
    fiscal_year: int = Field(ge=2020, le=2100)
    jurisdiction: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    revenue: Decimal | None = None
    pbt: Decimal | None = None
    covered_taxes: Decimal | None = None
    payroll: Decimal | None = None
    tangible_assets: Decimal | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("jurisdiction")
    @classmethod
    def recognized_jurisdiction(cls, value: str) -> str:
        """Reject free-text pollution and canonicalise common aliases (US -> United States)."""
        canonical = normalize_jurisdiction(value)
        if canonical not in CANONICAL_JURISDICTIONS:
            raise ValueError(f'"{value}" is not a recognised country/region for Jurisdiction')
        return canonical


class FinancialDataRead(FinancialDataCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_submitted: bool
    is_approved: bool
    requires_manual_confirmation: bool
    return_reason: str | None = None
    ai_anomaly_flags: dict | None = None
    missing_suggestion: dict | None = None


class ReturnRequest(BaseModel):
    """Optional reason HQ attaches when returning a submission."""
    reason: str | None = Field(default=None, max_length=500)


class MappingSuggestion(BaseModel):
    source_field: str
    target_field: str
    confidence: Decimal = Field(ge=0, le=1)


class MappingSuggestRequest(BaseModel):
    source_fields: list[str] = Field(min_length=1)


class MappingConfirmRequest(BaseModel):
    mappings: list[MappingSuggestion] = Field(min_length=1)


class TestResultRead(BaseModel):
    result: str
    explanation: str
    value: Decimal | None = None
    threshold: Decimal | None = None
    payroll_rate: Decimal | None = None
    asset_rate: Decimal | None = None


class EvaluationRead(BaseModel):
    tests: dict[str, TestResultRead]
    final_result: str
    warning: str | None


# AI Service Schemas
class AnomalyDetectionRequest(BaseModel):
    company_id: str
    fiscal_year: int
    jurisdiction: str
    revenue: Decimal | None = None
    pbt: Decimal | None = None
    covered_taxes: Decimal | None = None
    payroll: Decimal | None = None
    tangible_assets: Decimal | None = None


class AnomalyFlag(BaseModel):
    type: str  # "ratio_anomaly", "volatility_anomaly", "missing_critical"
    field: str
    message: str
    severity: str  # "warning", "error"


class AnomalyDetectionResponse(BaseModel):
    anomalies: list[AnomalyFlag]


class SuggestMissingRequest(BaseModel):
    company_id: str
    field_name: str


class SuggestMissingResponse(BaseModel):
    field_name: str
    suggested_value: Decimal | None
    confidence: float
    explanation: str


class BriefingResponse(BaseModel):
    briefing: str
    generated_at: str


class ChatRequest(BaseModel):
    message: str
    jurisdiction: str | None = None


class ChatResponse(BaseModel):
    reply: str


# Stage 3 — CSV batch upload schemas
class ColumnMappingInfo(BaseModel):
    csv_name: str
    mapped_field: str | None
    confidence: float = Field(ge=0, le=1)
    sample_values: list[str] = []


class BatchUploadResponse(BaseModel):
    columns: list[ColumnMappingInfo]
    preview_data: list[dict]
    rows: list[dict] = Field(default_factory=list)
    total_rows: int
    fiscal_year: int


class BatchRowInput(BaseModel):
    jurisdiction: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    revenue: Decimal | None = None
    pbt: Decimal | None = None
    covered_taxes: Decimal | None = None
    payroll: Decimal | None = None
    tangible_assets: Decimal | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class BatchCommitRequest(BaseModel):
    company_id: str
    fiscal_year: int = Field(ge=2020, le=2100)
    rows: list[BatchRowInput] = Field(min_length=1)


class BatchCommitResponse(BaseModel):
    success_count: int
    failed_rows: list[dict]


class BatchSubmitRequest(BaseModel):
    company_id: str
    fiscal_year: int = Field(ge=2020, le=2100)


class BatchSubmitResponse(BaseModel):
    submitted_count: int


class BatchApproveResponse(BaseModel):
    approved_count: int
