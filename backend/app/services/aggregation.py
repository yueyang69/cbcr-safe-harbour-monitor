from decimal import Decimal
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import FinancialData, JurisdictionSummary
from .safe_harbour import evaluate_safe_harbour


async def rebuild_summaries(session: AsyncSession, fiscal_year: int | None = None) -> list[JurisdictionSummary]:
    query = select(FinancialData).where(FinancialData.is_submitted.is_(True), FinancialData.is_approved.is_(True))
    if fiscal_year is not None:
        query = query.where(FinancialData.fiscal_year == fiscal_year)
    rows = list((await session.scalars(query)).all())
    years = {row.fiscal_year for row in rows}
    if fiscal_year is not None:
        years.add(fiscal_year)
    for year in years:
        await session.execute(delete(JurisdictionSummary).where(JurisdictionSummary.fiscal_year == year))
    grouped: dict[tuple[str, int], list[FinancialData]] = {}
    for row in rows:
        grouped.setdefault((row.jurisdiction, row.fiscal_year), []).append(row)
    summaries = []
    for (jurisdiction, year), items in grouped.items():
        def total(field: str) -> Decimal | None:
            values = [getattr(item, field) for item in items]
            return sum(values, Decimal("0")) if all(value is not None for value in values) else None
        evaluation = evaluate_safe_harbour(
            revenue=total("revenue"), pbt=total("pbt"), covered_taxes=total("covered_taxes"),
            payroll=total("payroll"), assets=total("tangible_assets"), fiscal_year=year,
        )
        summary = JurisdictionSummary(
            jurisdiction=jurisdiction, fiscal_year=year, revenue=total("revenue"), pbt=total("pbt"),
            covered_taxes=total("covered_taxes"), payroll=total("payroll"), tangible_assets=total("tangible_assets"),
            company_count=len(items), included_count=len(items), status=evaluation["final_result"],
            evaluation=serialize_evaluation(evaluation), warnings=[evaluation["warning"]] if evaluation["warning"] else [],
        )
        session.add(summary)
        summaries.append(summary)
    await session.commit()
    return summaries


def serialize_evaluation(evaluation: dict) -> dict:
    def serialize(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: serialize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [serialize(item) for item in value]
        return value

    return serialize({
        "tests": {name: vars(result) for name, result in evaluation["tests"].items()},
        "final_result": evaluation["final_result"],
        "warning": evaluation["warning"],
    })
