"""AI service for intelligent field mapping, anomaly detection, and risk briefing.

CRITICAL BOUNDARY: This module NEVER touches Safe Harbour core calculations.
All AI outputs require human confirmation before persisting to database.
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FinancialData, JurisdictionSummary

# Timeout for all AI operations (5 seconds as per requirements)
AI_TIMEOUT = 5.0

# Confidence threshold for auto-suggestions
CONFIDENCE_THRESHOLD = 0.6

# MiniMax API configuration
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "<your-minimax-api-key>")
MINIMAX_API_BASE = os.getenv("MINIMAX_API_BASE", "https://api.minimaxi.com/v1")

D = Decimal


class AIServiceError(Exception):
    """Raised when AI service is unavailable or times out."""


class AIService:
    """AI service with MiniMax LLM integration and deterministic fallbacks.

    Gracefully degrades to mock responses when API is unavailable.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.use_real_llm = bool(MINIMAX_API_KEY and MINIMAX_API_KEY.startswith("sk-"))

    async def _call_minimax(self, messages: list[dict], json_mode: bool = False, timeout: float = AI_TIMEOUT) -> dict | str:
        """Call MiniMax API with timeout and error handling.

        Returns parsed response or raises AIServiceError.
        """
        if not self.use_real_llm:
            # Fallback to mock for development/testing
            return await self._mock_response(messages, json_mode)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                payload = {
                    "model": "abab6.5-chat",  # MiniMax's latest model
                    "messages": messages,
                    "temperature": 0.1,  # Low temperature for consistent tax data responses
                }

                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                response = await client.post(
                    f"{MINIMAX_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {MINIMAX_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                response.raise_for_status()
                result = response.json()

                # Extract content from MiniMax response
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                if json_mode:
                    return json.loads(content) if content else {}
                return content

        except httpx.TimeoutException as error:
            raise AIServiceError("AI service timeout") from error
        except httpx.HTTPStatusError as error:
            raise AIServiceError(f"AI API error: {error.response.status_code}") from error
        except json.JSONDecodeError as error:
            raise AIServiceError(f"Invalid JSON response from AI: {error}") from error
        except Exception as error:
            raise AIServiceError(f"AI service error: {error}") from error

    async def _mock_response(self, messages: list[dict], json_mode: bool) -> dict | str:
        """Mock LLM response for testing/fallback."""
        await asyncio.sleep(0.1)  # Simulate network delay

        last_message = messages[-1]["content"].lower()

        if "field mapping" in last_message or "map" in last_message:
            return {"mappings": []} if json_mode else "无法识别字段"
        elif "anomaly" in last_message:
            return {"anomalies": []} if json_mode else "未检测到异常"
        elif "briefing" in last_message or "简报" in last_message:
            return "AI服务暂时不可用，请稍后重试。"
        elif "question" in last_message or "explain" in last_message:
            return "此问题超出我的能力范围，请联系您的税务顾问。"

        return {"status": "ok"} if json_mode else "收到"

    async def _mock_llm_call(self, prompt: str, json_mode: bool = False, timeout: float = AI_TIMEOUT) -> dict | str:
        """Legacy method for backward compatibility. Redirects to _call_minimax."""
        messages = [{"role": "user", "content": prompt}]
        return await self._call_minimax(messages, json_mode, timeout)

    async def suggest_field_mapping(self, source_fields: list[str]) -> list[dict[str, Any]]:
        """Smart field mapping with AI fallback for unknown fields.

        Returns Top 3 candidates with confidence scores.
        Fields with confidence < 60% force manual selection.
        """
        # Enhanced hardcoded dictionary with confidence scores
        ALIASES = {
            # 精确匹配（高置信度）
            "所在国家/地区": ("jurisdiction", 0.98),
            "jurisdiction": ("jurisdiction", 1.0),
            "辖区": ("jurisdiction", 0.95),
            "国家": ("jurisdiction", 0.92),
            "country": ("jurisdiction", 0.96),

            "报告期": ("fiscal_year", 0.98),
            "fiscal year": ("fiscal_year", 1.0),
            "会计年度": ("fiscal_year", 0.96),
            "年度": ("fiscal_year", 0.90),
            "year": ("fiscal_year", 0.88),

            "本位币": ("currency", 0.97),
            "currency": ("currency", 1.0),
            "币种": ("currency", 0.94),
            "货币": ("currency", 0.92),

            "全年营业收入": ("revenue", 0.96),
            "revenue": ("revenue", 1.0),
            "cbcr revenue": ("revenue", 0.98),
            "营业收入": ("revenue", 0.93),
            "收入": ("revenue", 0.85),
            "销售收入": ("revenue", 0.90),

            "税前利润": ("pbt", 0.99),
            "profit before tax": ("pbt", 1.0),
            "pbt": ("pbt", 1.0),
            "cbcr pbt": ("pbt", 0.98),
            "利润总额": ("pbt", 0.94),
            "利润": ("pbt", 0.82),

            "已涵盖所得税": ("covered_taxes", 0.94),
            "covered taxes": ("covered_taxes", 1.0),
            "simplified covered taxes": ("covered_taxes", 0.98),
            "所得税": ("covered_taxes", 0.88),
            "税费": ("covered_taxes", 0.80),

            "合格员工薪酬": ("payroll", 0.93),
            "eligible payroll": ("payroll", 1.0),
            "eligible payroll costs": ("payroll", 1.0),
            "payroll": ("payroll", 0.95),
            "员工薪酬": ("payroll", 0.89),
            "工资": ("payroll", 0.85),
            "人工成本": ("payroll", 0.87),

            "合格有形资产": ("tangible_assets", 0.96),
            "eligible tangible assets": ("tangible_assets", 1.0),
            "tangible assets": ("tangible_assets", 0.98),
            "有形资产": ("tangible_assets", 0.90),
            "固定资产": ("tangible_assets", 0.83),
        }

        suggestions = []
        unknown_fields = []

        # First pass: check enhanced hardcoded dictionary
        for source in source_fields:
            lookup_key = source.strip().lower()
            mapping = ALIASES.get(lookup_key)
            if mapping:
                target_field, confidence = mapping
                suggestions.append({
                    "source_field": source,
                    "target_field": target_field,
                    "confidence": confidence,
                })
            else:
                unknown_fields.append(source)

        # Second pass: AI inference for unknown fields
        if unknown_fields:
            try:
                messages = [
                    {"role": "system", "content": "You are a field mapping assistant for CbCR tax data. Map field names to standard fields."},
                    {"role": "user", "content": f"""Map these field names to standard CbCR fields: {', '.join(unknown_fields)}

Standard fields: jurisdiction, fiscal_year, revenue, pbt, covered_taxes, payroll, tangible_assets, currency

Return JSON array with format: {{"mappings": [{{"source": "field name", "target": "standard_field", "confidence": 0.0-1.0}}]}}
Only return the JSON, no explanation."""}
                ]

                response = await asyncio.wait_for(
                    self._call_minimax(messages, json_mode=True),
                    timeout=AI_TIMEOUT
                )

                if isinstance(response, dict) and "mappings" in response:
                    for mapping in response["mappings"]:
                        suggestions.append({
                            "source_field": mapping.get("source", ""),
                            "target_field": mapping.get("target", "revenue"),
                            "confidence": mapping.get("confidence", 0.5),
                        })

            except (AIServiceError, asyncio.TimeoutError):
                # Graceful degradation: return low-confidence suggestions
                for field in unknown_fields:
                    suggestions.append({
                        "source_field": field,
                        "target_field": "revenue",  # Safe default
                        "confidence": 0.3,  # Below threshold, forces manual selection
                    })

        return suggestions

    async def detect_anomalies(
        self,
        company_id: str,
        fiscal_year: int,
        jurisdiction: str,
        revenue: Decimal | None,
        pbt: Decimal | None,
        covered_taxes: Decimal | None,
        payroll: Decimal | None,
        tangible_assets: Decimal | None,
    ) -> list[dict[str, str]]:
        """Detect three types of anomalies: ratio, volatility, missing critical fields.

        WARNING ONLY - never auto-modify values.
        """
        anomalies = []

        # 1. Ratio anomaly: ETR out of bounds
        if covered_taxes is not None and pbt is not None and pbt != 0:
            etr = covered_taxes / pbt
            if etr > 1.0 or etr < 0:
                anomalies.append({
                    "type": "ratio_anomaly",
                    "field": "covered_taxes",
                    "message": f"ETR 异常 ({etr:.1%})，请确认是否漏填免税收入或会计差错",
                    "severity": "error",
                })

        # 2. Volatility anomaly: compare with prior year
        try:
            prev_year_query = select(FinancialData).where(
                FinancialData.company_id == company_id,
                FinancialData.fiscal_year == fiscal_year - 1,
                FinancialData.is_approved.is_(True),
            )
            prev_year_data = (await self.session.scalars(prev_year_query)).first()

            if prev_year_data:
                for field_name, current_value in [
                    ("revenue", revenue),
                    ("pbt", pbt),
                    ("covered_taxes", covered_taxes),
                    ("payroll", payroll),
                    ("tangible_assets", tangible_assets),
                ]:
                    prev_value = getattr(prev_year_data, field_name)
                    if current_value is not None and prev_value is not None and prev_value != 0:
                        change_pct = (current_value - prev_value) / abs(prev_value)
                        if abs(change_pct) > 2.0:  # ±200%
                            anomalies.append({
                                "type": "volatility_anomaly",
                                "field": field_name,
                                "message": f"{field_name} 较去年变化 {change_pct:.0%}，请确认业务变动或数据录入错误",
                                "severity": "warning",
                            })

        except Exception:
            # If historical data query fails, skip volatility check
            pass

        # 3. Missing critical fields
        critical_fields = [
            ("payroll", payroll, "此字段缺失，将导致 Routine Profits Test 无法计算"),
            ("tangible_assets", tangible_assets, "此字段缺失，将导致 Routine Profits Test 无法计算"),
            ("covered_taxes", covered_taxes, "此字段缺失，将导致 Simplified ETR Test 无法计算"),
        ]

        for field_name, value, message in critical_fields:
            if value is None:
                anomalies.append({
                    "type": "missing_critical",
                    "field": field_name,
                    "message": message,
                    "severity": "warning",
                })

        return anomalies

    async def suggest_missing_value(self, company_id: str, field_name: str) -> dict[str, Any]:
        """Suggest missing value based on historical data (median/average).

        Returns suggestion with confidence and explanation.
        """
        try:
            # Query historical data for this company
            query = select(FinancialData).where(
                FinancialData.company_id == company_id,
                FinancialData.is_approved.is_(True),
            ).order_by(FinancialData.fiscal_year.desc()).limit(5)

            historical_data = list((await self.session.scalars(query)).all())

            if not historical_data:
                return {
                    "field_name": field_name,
                    "suggested_value": None,
                    "confidence": 0.0,
                    "explanation": "无历史数据可供参考",
                }

            # Extract values for the target field
            values = [getattr(row, field_name) for row in historical_data if getattr(row, field_name) is not None]

            if not values:
                return {
                    "field_name": field_name,
                    "suggested_value": None,
                    "confidence": 0.0,
                    "explanation": f"历史记录中 {field_name} 均为空",
                }

            # Calculate median (more robust than mean for outliers)
            suggested_value = Decimal(str(statistics.median(float(v) for v in values)))
            years = [row.fiscal_year for row in historical_data if getattr(row, field_name) is not None]
            year_range = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])

            return {
                "field_name": field_name,
                "suggested_value": suggested_value,
                "confidence": min(0.95, 0.6 + len(values) * 0.1),  # Confidence increases with data points
                "explanation": f"建议填充 {field_name} = {suggested_value:,.2f}（基于 {year_range} 年历史中位数）",
            }

        except Exception as error:
            return {
                "field_name": field_name,
                "suggested_value": None,
                "confidence": 0.0,
                "explanation": f"无法生成建议：{error}",
            }

    async def generate_risk_briefing(self, fiscal_year: int | None = None) -> dict[str, str]:
        """Generate natural language risk briefing (max 200 Chinese characters).

        Summarizes high-risk jurisdictions, gap metrics, and priority recommendations.
        """
        try:
            # Query all jurisdiction summaries
            query = select(JurisdictionSummary)
            if fiscal_year is not None:
                query = query.where(JurisdictionSummary.fiscal_year == fiscal_year)

            summaries = list((await self.session.scalars(query)).all())

            if not summaries:
                return {
                    "briefing": f"暂无 FY {fiscal_year or '所有年度'} 的辖区数据。",
                    "generated_at": datetime.now(UTC).isoformat(),
                }

            # Analyze risk jurisdictions
            fail_jurisdictions = [s for s in summaries if s.status == "WARNING"]
            incomplete_jurisdictions = [s for s in summaries if s.status == "INCOMPLETE"]

            briefing_parts = []

            # High-risk summary
            if fail_jurisdictions:
                fail_names = "、".join([j.jurisdiction for j in fail_jurisdictions[:3]])
                if len(fail_jurisdictions) > 3:
                    fail_names += f"等{len(fail_jurisdictions)}个辖区"
                briefing_parts.append(f"⚠️ {len(fail_jurisdictions)}个高风险辖区（{fail_names}）三项测试全部FAIL。")

                # Highlight specific gaps
                for jurisdiction_summary in fail_jurisdictions[:2]:  # Top 2 only
                    if jurisdiction_summary.evaluation:
                        etr_test = jurisdiction_summary.evaluation.get("tests", {}).get("simplified_etr", {})
                        if etr_test.get("result") == "FAIL" and etr_test.get("value") and etr_test.get("threshold"):
                            etr_val = float(etr_test["value"])
                            threshold = float(etr_test["threshold"])
                            gap = (threshold - etr_val) * 100
                            briefing_parts.append(f"{jurisdiction_summary.jurisdiction} ETR {etr_val:.1%} < {threshold:.0%}，缺口{gap:.1f}%。")

            if incomplete_jurisdictions:
                briefing_parts.append(f"另有{len(incomplete_jurisdictions)}个辖区数据不完整。")

            # Priority recommendation
            if fail_jurisdictions:
                top_risks = ", ".join([j.jurisdiction for j in fail_jurisdictions[:2]])
                briefing_parts.append(f"建议优先复核{top_risks}的数据口径。")

            briefing_text = " ".join(briefing_parts)

            # Truncate to 200 characters if needed
            if len(briefing_text) > 200:
                briefing_text = briefing_text[:197] + "..."

            # If no risks, provide positive summary
            if not fail_jurisdictions and not incomplete_jurisdictions:
                briefing_text = f"✓ 所有{len(summaries)}个辖区均通过Safe Harbour测试或数据完整。"

            return {
                "briefing": briefing_text,
                "generated_at": datetime.now(UTC).isoformat(),
            }

        except Exception as error:
            return {
                "briefing": f"AI简报生成失败：{error}。请手动查看Dashboard。",
                "generated_at": datetime.now(UTC).isoformat(),
            }

    async def chat_assistant(self, message: str, jurisdiction: str | None = None) -> dict[str, str]:
        """Tax data Q&A assistant with strict scope limitation.

        System prompt FORBIDS tax calculation advice or legal opinions.
        Only explains existing computed values.
        """
        # Prepare context data
        context_data = {}
        if jurisdiction:
            try:
                query = select(JurisdictionSummary).where(
                    JurisdictionSummary.jurisdiction == jurisdiction
                ).order_by(JurisdictionSummary.fiscal_year.desc()).limit(1)

                summary = (await self.session.scalars(query)).first()
                if summary:
                    context_data = {
                        "jurisdiction": summary.jurisdiction,
                        "fiscal_year": summary.fiscal_year,
                        "revenue": str(summary.revenue) if summary.revenue else None,
                        "pbt": str(summary.pbt) if summary.pbt else None,
                        "status": summary.status,
                        "evaluation": summary.evaluation,
                    }
            except Exception:
                pass

        # Build strict system prompt
        system_prompt = """你是一个税务数据助手，只能回答关于本系统已计算出的 PBT、ETR、SBIE、De minimis 结果等数值的解释。
你的回答必须基于系统返回的数据，禁止给出任何补足税计算建议、避税方案或法律意见。
如果问题超出范围，统一回复：'此问题超出我的能力范围，请联系您的税务顾问。'

当前辖区数据：
""" + str(context_data)

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]

            response = await asyncio.wait_for(
                self._call_minimax(messages, json_mode=False),
                timeout=AI_TIMEOUT
            )

            if isinstance(response, str) and response.strip():
                return {"reply": response}
            elif isinstance(response, dict) and "reply" in response:
                return {"reply": response["reply"]}
            else:
                return {"reply": "此问题超出我的能力范围，请联系您的税务顾问。"}

        except (AIServiceError, asyncio.TimeoutError):
            return {"reply": "AI助手暂时不可用，请稍后重试或联系您的税务顾问。"}
