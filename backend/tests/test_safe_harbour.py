from decimal import Decimal
from app.services.safe_harbour import (
    carve_out_rates,
    de_minimis,
    etr_threshold,
    evaluate_safe_harbour,
    routine_profits,
    simplified_etr,
)

D = Decimal


def test_de_minimis_boundary_passes():
    result = de_minimis(D("10000000"), D("1000000"))
    assert result.result == "PASS"


def test_de_minimis_over_boundary_fails():
    assert de_minimis(D("10000000.01"), D("1000000")).result == "FAIL"
    assert de_minimis(D("10000000"), D("1000000.01")).result == "FAIL"


def test_missing_de_minimis_data_is_incomplete():
    assert de_minimis(None, D("1")).result == "INCOMPLETE"


def test_etr_thresholds_and_equal_threshold_passes():
    assert etr_threshold(2024) == D("0.15")
    assert etr_threshold(2025) == D("0.16")
    assert etr_threshold(2026) == D("0.17")
    assert simplified_etr(D("16"), D("100"), 2025).result == "PASS"
    assert simplified_etr(D("16"), D("100"), 2025).value == D("0.16")


def test_etr_below_threshold_fails_and_zero_pbt_is_incomplete():
    assert simplified_etr(D("15.99"), D("100"), 2025).result == "FAIL"
    assert simplified_etr(D("0"), D("0"), 2025).result == "INCOMPLETE"


def test_carve_out_rates_constant_simplification():
    # 简化假设：不分年度，统一 10%/8%（参见 claude.md）
    assert carve_out_rates(2024) == (D("0.10"), D("0.08"))
    assert carve_out_rates(2025) == (D("0.10"), D("0.08"))
    assert carve_out_rates(2028) == (D("0.10"), D("0.08"))


def test_routine_profits_uses_constant_rates_and_boundary_passes():
    result = routine_profits(D("1000"), D("1000"), D("180"), 2024)
    assert result.result == "PASS"
    assert result.value == D("180.0")
    assert result.payroll_rate == D("0.10")
    assert result.asset_rate == D("0.08")
    assert routine_profits(D("1000"), D("1000"), D("180.01"), 2024).result == "FAIL"


def test_all_fail_stops_at_warning_without_tax_calculation():
    result = evaluate_safe_harbour(
        revenue=D("20000000"), pbt=D("2000000"), covered_taxes=D("0"),
        payroll=D("0"), assets=D("0"), fiscal_year=2025,
    )
    assert result["final_result"] == "WARNING"
    assert "GloBE" in result["warning"]
    assert "top_up_tax" not in result


def test_missing_data_does_not_become_tax_fail():
    result = evaluate_safe_harbour(
        revenue=None, pbt=D("100"), covered_taxes=None,
        payroll=D("1"), assets=None, fiscal_year=2026,
    )
    assert result["final_result"] == "INCOMPLETE"
