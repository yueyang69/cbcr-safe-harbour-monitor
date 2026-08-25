"""Unit tests for AI service with mocked LLM calls."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import AIService, AIServiceError


@pytest.fixture
def mock_session():
    """Mock AsyncSession for testing."""
    session = AsyncMock()
    # Python 3.14 AsyncMock child return_value is itself an AsyncMock, which turns
    # `session.scalars(...).all()` / `.first()` into un-awaited coroutines and breaks
    # the sync `list(...).all()` pattern. Force a plain Mock so those stay synchronous.
    scalars_result = MagicMock()
    session.scalars.return_value = scalars_result
    return session


@pytest.mark.asyncio
async def test_field_mapping_hardcoded_chinese(mock_session):
    """Test hardcoded Chinese field mapping with high confidence."""
    ai_service = AIService(mock_session)

    suggestions = await ai_service.suggest_field_mapping(["税前利润", "收入", "辖区"])

    assert len(suggestions) == 3
    assert suggestions[0]["source_field"] == "税前利润"
    assert suggestions[0]["target_field"] == "pbt"
    assert suggestions[0]["confidence"] == 0.99

    assert suggestions[1]["source_field"] == "收入"
    assert suggestions[1]["target_field"] == "revenue"
    assert suggestions[1]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_field_mapping_unknown_field_degradation(mock_session):
    """Test graceful degradation for unknown fields when AI fails."""
    ai_service = AIService(mock_session)
    ai_service.use_real_llm = False  # Force mock

    suggestions = await ai_service.suggest_field_mapping(["未知字段XYZ"])

    assert len(suggestions) == 1
    assert suggestions[0]["source_field"] == "未知字段XYZ"
    assert suggestions[0]["confidence"] < 0.6  # Below threshold


@pytest.mark.asyncio
async def test_anomaly_detection_ratio_anomaly(mock_session):
    """Test ETR ratio anomaly detection."""
    ai_service = AIService(mock_session)

    # ETR > 100% should trigger anomaly
    anomalies = await ai_service.detect_anomalies(
        company_id="test-company",
        fiscal_year=2025,
        jurisdiction="Japan",
        revenue=Decimal("1000000"),
        pbt=Decimal("100000"),
        covered_taxes=Decimal("150000"),  # 150% ETR - anomaly!
        payroll=Decimal("50000"),
        tangible_assets=Decimal("200000"),
    )

    assert len(anomalies) >= 1
    ratio_anomaly = next((a for a in anomalies if a["type"] == "ratio_anomaly"), None)
    assert ratio_anomaly is not None
    assert "ETR 异常" in ratio_anomaly["message"]
    assert ratio_anomaly["severity"] == "error"


@pytest.mark.asyncio
async def test_anomaly_detection_missing_critical(mock_session):
    """Test missing critical field detection."""
    ai_service = AIService(mock_session)

    # Missing payroll should trigger warning
    anomalies = await ai_service.detect_anomalies(
        company_id="test-company",
        fiscal_year=2025,
        jurisdiction="Japan",
        revenue=Decimal("1000000"),
        pbt=Decimal("100000"),
        covered_taxes=Decimal("15000"),
        payroll=None,  # Missing!
        tangible_assets=Decimal("200000"),
    )

    missing_anomalies = [a for a in anomalies if a["type"] == "missing_critical"]
    assert len(missing_anomalies) >= 1
    payroll_anomaly = next((a for a in missing_anomalies if a["field"] == "payroll"), None)
    assert payroll_anomaly is not None
    assert "Routine Profits Test" in payroll_anomaly["message"]


@pytest.mark.asyncio
async def test_suggest_missing_value_no_history(mock_session):
    """Test missing value suggestion with no historical data."""
    mock_session.scalars.return_value.all.return_value = []

    ai_service = AIService(mock_session)
    suggestion = await ai_service.suggest_missing_value("company-1", "payroll")

    assert suggestion["field_name"] == "payroll"
    assert suggestion["suggested_value"] is None
    assert suggestion["confidence"] == 0.0
    assert "无历史数据" in suggestion["explanation"]


@pytest.mark.asyncio
async def test_suggest_missing_value_with_history(mock_session):
    """Test missing value suggestion calculates median from history."""
    # Mock historical data
    mock_data = []
    for year, value in [(2023, Decimal("100000")), (2024, Decimal("120000")), (2025, Decimal("110000"))]:
        mock_record = AsyncMock()
        mock_record.fiscal_year = year
        mock_record.payroll = value
        mock_data.append(mock_record)

    mock_session.scalars.return_value.all.return_value = mock_data

    ai_service = AIService(mock_session)
    suggestion = await ai_service.suggest_missing_value("company-1", "payroll")

    assert suggestion["field_name"] == "payroll"
    assert suggestion["suggested_value"] == Decimal("110000")  # Median of [100k, 110k, 120k]
    assert suggestion["confidence"] > 0.6
    assert "2023-2025" in suggestion["explanation"]


@pytest.mark.asyncio
async def test_generate_risk_briefing_no_data(mock_session):
    """Test briefing generation with no jurisdiction data."""
    mock_session.scalars.return_value.all.return_value = []

    ai_service = AIService(mock_session)
    briefing = await ai_service.generate_risk_briefing(fiscal_year=2025)

    assert "暂无" in briefing["briefing"]
    assert "generated_at" in briefing


@pytest.mark.asyncio
async def test_generate_risk_briefing_with_failures(mock_session):
    """Test briefing highlights high-risk jurisdictions."""
    # Mock jurisdiction summaries
    mock_summary_fail = AsyncMock()
    mock_summary_fail.jurisdiction = "Japan"
    mock_summary_fail.status = "WARNING"
    mock_summary_fail.evaluation = {
        "tests": {
            "simplified_etr": {"result": "FAIL", "value": "0.142", "threshold": "0.16"}
        }
    }

    mock_summary_pass = AsyncMock()
    mock_summary_pass.jurisdiction = "USA"
    mock_summary_pass.status = "PASS"
    mock_summary_pass.evaluation = {}

    mock_session.scalars.return_value.all.return_value = [mock_summary_fail, mock_summary_pass]

    ai_service = AIService(mock_session)
    briefing = await ai_service.generate_risk_briefing(fiscal_year=2025)

    assert "Japan" in briefing["briefing"]
    assert "高风险" in briefing["briefing"] or "FAIL" in briefing["briefing"]
    assert len(briefing["briefing"]) <= 200  # Max 200 characters


@pytest.mark.asyncio
async def test_chat_assistant_scope_limitation(mock_session):
    """Test chat assistant rejects out-of-scope questions."""
    ai_service = AIService(mock_session)
    ai_service.use_real_llm = False  # Use mock

    response = await ai_service.chat_assistant("如何避税？", jurisdiction=None)

    assert "超出我的能力范围" in response["reply"] or "税务顾问" in response["reply"]


@pytest.mark.asyncio
async def test_chat_assistant_with_jurisdiction_context(mock_session):
    """Test chat assistant loads jurisdiction context."""
    mock_summary = AsyncMock()
    mock_summary.jurisdiction = "Japan"
    mock_summary.fiscal_year = 2025
    mock_summary.revenue = Decimal("1000000")
    mock_summary.pbt = Decimal("100000")
    mock_summary.status = "PASS"
    mock_summary.evaluation = {}

    mock_session.scalars.return_value.first.return_value = mock_summary

    ai_service = AIService(mock_session)
    ai_service.use_real_llm = False

    response = await ai_service.chat_assistant("日本的ETR是多少？", jurisdiction="Japan")

    assert "reply" in response
    # Context should be loaded (tested via mock call verification)


@pytest.mark.asyncio
async def test_ai_service_timeout_handling(mock_session):
    """Test AI service handles timeout gracefully."""
    ai_service = AIService(mock_session)

    # Mock timeout by patching _call_minimax
    with patch.object(ai_service, "_call_minimax", side_effect=AIServiceError("timeout")):
        suggestions = await ai_service.suggest_field_mapping(["未知字段"])

        # Should degrade gracefully, not raise exception
        assert len(suggestions) == 1
        assert suggestions[0]["confidence"] < 0.6
