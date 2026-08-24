"""Deterministic Transitional CbCR Safe Harbour warning rules."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

D = Decimal

ETR_THRESHOLDS = {2024: D("0.15"), 2025: D("0.16")}
DEFAULT_ETR_THRESHOLD = D("0.17")
CARVE_OUT_RATES = {
    2024: (D("0.098"), D("0.078")),
    2025: (D("0.096"), D("0.076")),
    2026: (D("0.094"), D("0.074")),
    2027: (D("0.092"), D("0.072")),
}
DEFAULT_CARVE_OUT_RATES = (D("0.090"), D("0.070"))

@dataclass(frozen=True)
class TestResult:
    result: str
    explanation: str
    value: Optional[Decimal] = None
    threshold: Optional[Decimal] = None
    payroll_rate: Optional[Decimal] = None
    asset_rate: Optional[Decimal] = None


def etr_threshold(fiscal_year: int) -> Decimal:
    return ETR_THRESHOLDS.get(fiscal_year, DEFAULT_ETR_THRESHOLD)


def carve_out_rates(fiscal_year: int) -> tuple[Decimal, Decimal]:
    return CARVE_OUT_RATES.get(fiscal_year, DEFAULT_CARVE_OUT_RATES)


def de_minimis(revenue: Optional[Decimal], pbt: Optional[Decimal]) -> TestResult:
    if revenue is None or pbt is None:
        return TestResult("INCOMPLETE", "Revenue 或 PBT 缺失，无法完成 De minimis 测试")
    if revenue <= D("10000000") and pbt <= D("1000000"):
        return TestResult("PASS", "Revenue <= EUR 10m 且 PBT <= EUR 1m")
    reasons = []
    if revenue > D("10000000"):
        reasons.append(f"Revenue {revenue:,.2f} > EUR 10m")
    if pbt > D("1000000"):
        reasons.append(f"PBT {pbt:,.2f} > EUR 1m")
    return TestResult("FAIL", "；".join(reasons))


def simplified_etr(
    covered_taxes: Optional[Decimal], pbt: Optional[Decimal], fiscal_year: int
) -> TestResult:
    threshold = etr_threshold(fiscal_year)
    if covered_taxes is None or pbt is None:
        return TestResult("INCOMPLETE", "Covered Taxes 或 PBT 缺失，无法计算 Simplified ETR", threshold=threshold)
    if pbt == 0:
        return TestResult("INCOMPLETE", "PBT 为 0，Simplified ETR 不可计算", threshold=threshold)
    etr = covered_taxes / pbt
    if etr >= threshold:
        return TestResult("PASS", f"Simplified ETR {etr:.2%} >= FY{fiscal_year} threshold {threshold:.0%}", etr, threshold)
    return TestResult("FAIL", f"Simplified ETR {etr:.2%} < FY{fiscal_year} threshold {threshold:.0%}", etr, threshold)


def routine_profits(
    payroll: Optional[Decimal], assets: Optional[Decimal], pbt: Optional[Decimal], fiscal_year: int
) -> TestResult:
    payroll_rate, asset_rate = carve_out_rates(fiscal_year)
    if payroll is None or assets is None or pbt is None:
        return TestResult("INCOMPLETE", "Payroll、Tangible Assets 或 PBT 缺失，无法计算 SBIE", payroll_rate=payroll_rate, asset_rate=asset_rate)
    sbie = payroll * payroll_rate + assets * asset_rate
    if pbt <= sbie:
        return TestResult(
            "PASS",
            f"PBT {pbt:,.2f} <= SBIE {sbie:,.2f}",
            value=sbie,
            payroll_rate=payroll_rate,
            asset_rate=asset_rate,
        )
    return TestResult(
        "FAIL",
        f"PBT {pbt:,.2f} > SBIE {sbie:,.2f}",
        value=sbie,
        payroll_rate=payroll_rate,
        asset_rate=asset_rate,
    )


def evaluate_safe_harbour(
    *, revenue: Optional[Decimal], pbt: Optional[Decimal], covered_taxes: Optional[Decimal],
    payroll: Optional[Decimal], assets: Optional[Decimal], fiscal_year: int,
) -> dict:
    tests = {
        "de_minimis": de_minimis(revenue, pbt),
        "simplified_etr": simplified_etr(covered_taxes, pbt, fiscal_year),
        "routine_profits": routine_profits(payroll, assets, pbt, fiscal_year),
    }
    results = [test.result for test in tests.values()]
    if "PASS" in results:
        final = "PASS"
        warning = None if all(value == "PASS" or value == "FAIL" for value in results) else "部分数据缺失，建议补齐后复核"
    elif all(value == "FAIL" for value in results):
        final = "WARNING"
        warning = "三项测试均 FAIL；本系统仅生成风险预警，请人工进行 GloBE 深度分析"
    else:
        final = "INCOMPLETE"
        warning = "数据不完整，无法得出完整 Safe Harbour 结论"
    return {"tests": tests, "final_result": final, "warning": warning}
