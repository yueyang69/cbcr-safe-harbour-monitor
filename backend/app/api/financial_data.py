import csv
import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import Role, current_entity, require_entity_scope, require_roles
from ..models import Company, FinancialData
from ..schemas import (
    BatchApproveResponse,
    BatchCommitRequest,
    BatchCommitResponse,
    BatchSubmitRequest,
    BatchSubmitResponse,
    BatchUploadResponse,
    FinancialDataCreate,
    FinancialDataRead,
)
from ..services.aggregation import rebuild_summaries
from ..services.column_mapper import map_columns

router = APIRouter(prefix="/financial-data", tags=["financial-data"])


async def get_company(session: AsyncSession, company_id: str) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


async def get_financial_data(session: AsyncSession, data_id: str) -> FinancialData:
    data = await session.get(FinancialData, data_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Financial data not found")
    return data


@router.post("", response_model=FinancialDataRead, status_code=status.HTTP_201_CREATED)
async def create_financial_data(payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    # Scope check before the 404 lookup so a subsidiary cannot probe whether another entity exists.
    require_entity_scope(role, entity_id, payload.company_id)
    await get_company(session, payload.company_id)
    existing = await session.scalar(select(FinancialData).where(FinancialData.company_id == payload.company_id, FinancialData.fiscal_year == payload.fiscal_year, FinancialData.jurisdiction == payload.jurisdiction))
    if existing:
        raise HTTPException(status_code=409, detail="Financial data already exists for company, fiscal year and jurisdiction")
    data = FinancialData(**payload.model_dump(), requires_manual_confirmation=payload.currency != "EUR")
    session.add(data)
    await session.commit()
    await session.refresh(data)
    return data


@router.post("/quick-submit", response_model=FinancialDataRead)
async def quick_submit_financial_data(payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    """MVP quick-test loop: upsert source data, auto-approve it, and rebuild
    jurisdiction summaries so it shows up on the Dashboard immediately.

    HQ/admin only — the approver enters and approves in one step. A subsidiary
    still follows the strict submit -> HQ approve flow and never sees the
    Dashboard (permission matrix unchanged).
    """
    await get_company(session, payload.company_id)
    data = await session.scalar(select(FinancialData).where(
        FinancialData.company_id == payload.company_id,
        FinancialData.fiscal_year == payload.fiscal_year,
        FinancialData.jurisdiction == payload.jurisdiction,
    ))
    if data is None:
        data = FinancialData(**payload.model_dump(), requires_manual_confirmation=payload.currency != "EUR")
        session.add(data)
    else:
        for field, value in payload.model_dump().items():
            setattr(data, field, value)
        data.requires_manual_confirmation = payload.currency != "EUR"
    data.is_submitted = True
    data.is_approved = True
    await session.commit()
    await rebuild_summaries(session, payload.fiscal_year)
    await session.refresh(data)
    return data


@router.post("/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_csv(
    file: UploadFile = File(...),
    fiscal_year: int = Form(...),
    company_id: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
    role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)),
    entity_id: str | None = Depends(current_entity),
):
    """Stage 3: parse a CSV of jurisdiction rows and suggest column mappings.

    Pure in-memory step — nothing is persisted here. A subsidiary is locked to
    its own entity (company_id is forced to X-Entity-Id); HQ/admin must pass an
    explicit company_id. Returns column mapping suggestions plus a 5-row preview
    for the human to confirm before calling /batch-commit.
    """
    if role == Role.SUBSIDIARY:
        if not entity_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Entity-Id header is required for subsidiary role")
        company_id = entity_id
    elif not company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_id is required for HQ/admin")
    require_entity_scope(role, entity_id, company_id)
    await get_company(session, company_id)

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode CSV as UTF-8 or GBK") from error

    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty or has no data rows")

    headers = [header.strip() for header in rows[0]]
    header_count = len(headers)
    data_rows = rows[1:]
    if not data_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file has no data rows (header only)")
    for idx, row in enumerate(data_rows, start=2):
        if len(row) != header_count:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Row {idx} has {len(row)} columns, expected {header_count}")

    sample_values = {
        header: [data_rows[r][col_idx] for r in range(min(3, len(data_rows))) if col_idx < len(data_rows[r])]
        for col_idx, header in enumerate(headers)
    }
    columns = map_columns(headers, sample_values)
    all_rows = [dict(zip(headers, row)) for row in data_rows]
    return BatchUploadResponse(
        columns=columns,
        preview_data=all_rows[:5],
        rows=all_rows,
        total_rows=len(data_rows),
        fiscal_year=fiscal_year,
    )


@router.post("/batch-commit", response_model=BatchCommitResponse)
async def batch_commit(
    payload: BatchCommitRequest,
    session: AsyncSession = Depends(get_session),
    role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)),
    entity_id: str | None = Depends(current_entity),
):
    """Stage 3: persist confirmed CSV rows as DRAFT financial_data records.

    Atomic: any row that would violate the (company_id, fiscal_year,
    jurisdiction) unique constraint aborts the whole commit with 409 — no
    partial writes. Successful rows are stored as drafts (is_submitted=False,
    is_approved=False) and must still flow through submit → HQ approve.
    """
    require_entity_scope(role, entity_id, payload.company_id)
    await get_company(session, payload.company_id)

    conflicts = []
    for idx, row in enumerate(payload.rows):
        existing = await session.scalar(select(FinancialData).where(
            FinancialData.company_id == payload.company_id,
            FinancialData.fiscal_year == payload.fiscal_year,
            FinancialData.jurisdiction == row.jurisdiction,
        ))
        if existing:
            conflicts.append({"row_index": idx, "error": f"Data already exists for {row.jurisdiction} in FY{payload.fiscal_year}"})

    if conflicts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Some rows conflict with existing data: {conflicts}")

    for row in payload.rows:
        session.add(FinancialData(
            company_id=payload.company_id,
            fiscal_year=payload.fiscal_year,
            jurisdiction=row.jurisdiction,
            currency=row.currency,
            revenue=row.revenue,
            pbt=row.pbt,
            covered_taxes=row.covered_taxes,
            payroll=row.payroll,
            tangible_assets=row.tangible_assets,
            is_submitted=False,
            is_approved=False,
            requires_manual_confirmation=row.currency != "EUR",
        ))
    await session.commit()
    return BatchCommitResponse(success_count=len(payload.rows), failed_rows=[])


@router.post("/batch-submit", response_model=BatchSubmitResponse)
async def batch_submit(
    payload: BatchSubmitRequest,
    session: AsyncSession = Depends(get_session),
    role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)),
    entity_id: str | None = Depends(current_entity),
):
    """Stage 3: submit every DRAFT row for a (company, fiscal_year) in one step.

    Marks is_submitted=True on all currently-unsubmitted rows, so an entire CSV
    import reaches HQ's approval queue with a single click instead of one
    draft at a time. Mirrors batch-commit's entity-scope rules; approved rows are
    left untouched.
    """
    require_entity_scope(role, entity_id, payload.company_id)
    await get_company(session, payload.company_id)

    rows = list((await session.scalars(select(FinancialData).where(
        FinancialData.company_id == payload.company_id,
        FinancialData.fiscal_year == payload.fiscal_year,
        FinancialData.is_submitted.is_(False),
    ))).all())
    for row in rows:
        row.is_submitted = True
    await session.commit()
    return BatchSubmitResponse(submitted_count=len(rows))


@router.post("/batch-approve", response_model=BatchApproveResponse)
async def batch_approve(
    session: AsyncSession = Depends(get_session),
    _: Role = Depends(require_roles(Role.HQ, Role.ADMIN)),
):
    """HQ approves the whole pending queue in one click and rebuilds the
    jurisdiction cache once, so every approved jurisdiction appears on the
    Dashboard immediately (the demo's '批量通过')."""
    rows = list((await session.scalars(select(FinancialData).where(
        FinancialData.is_submitted.is_(True),
        FinancialData.is_approved.is_(False),
    ))).all())
    for row in rows:
        row.is_approved = True
    years = {row.fiscal_year for row in rows}
    await session.commit()
    for year in years:
        await rebuild_summaries(session, year)
    return BatchApproveResponse(approved_count=len(rows))


@router.get("", response_model=list[FinancialDataRead])
async def list_financial_data(company_id: str | None = None, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.REVIEWER, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    query = select(FinancialData).order_by(FinancialData.fiscal_year.desc())
    if role == Role.SUBSIDIARY:
        if not entity_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Entity-Id header is required for subsidiary role")
        if company_id and company_id != entity_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subsidiary role is restricted to its own entity")
        query = query.where(FinancialData.company_id == entity_id)
    elif company_id:
        query = query.where(FinancialData.company_id == company_id)
    return list((await session.scalars(query)).all())


@router.post("/{data_id}/submit", response_model=FinancialDataRead)
async def submit_financial_data(data_id: str, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    data = await get_financial_data(session, data_id)
    require_entity_scope(role, entity_id, data.company_id)
    data.is_submitted = True
    await session.commit()
    await session.refresh(data)
    return data


@router.post("/{data_id}/approve", response_model=FinancialDataRead)
async def approve_financial_data(data_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    data = await get_financial_data(session, data_id)
    data.is_approved = True
    await session.commit()
    # Strict flow: approval is what publishes to the Dashboard, so rebuild the
    # jurisdiction cache immediately (quick-submit already does this in one step).
    await rebuild_summaries(session, data.fiscal_year)
    await session.refresh(data)
    return data


@router.post("/{data_id}/return", response_model=FinancialDataRead)
async def return_financial_data(data_id: str, session: AsyncSession = Depends(get_session), _: Role = Depends(require_roles(Role.HQ, Role.ADMIN))):
    """HQ returns submitted data so the reporting entity can edit it again."""
    data = await get_financial_data(session, data_id)
    data.is_submitted = False
    data.is_approved = False
    await session.commit()
    # A returned jurisdiction must leave the Dashboard until it is re-approved.
    await rebuild_summaries(session, data.fiscal_year)
    await session.refresh(data)
    return data


@router.put("/{data_id}", response_model=FinancialDataRead)
async def update_financial_data(data_id: str, payload: FinancialDataCreate, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    data = await get_financial_data(session, data_id)
    require_entity_scope(role, entity_id, data.company_id)
    require_entity_scope(role, entity_id, payload.company_id)
    if role == Role.SUBSIDIARY and data.is_submitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submitted data must be returned by HQ before editing")
    await get_company(session, payload.company_id)
    existing = await session.scalar(select(FinancialData).where(
        FinancialData.company_id == payload.company_id,
        FinancialData.fiscal_year == payload.fiscal_year,
        FinancialData.jurisdiction == payload.jurisdiction,
        FinancialData.id != data_id,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="Financial data already exists for company and year")
    for field, value in payload.model_dump().items():
        setattr(data, field, value)
    data.requires_manual_confirmation = payload.currency != "EUR"
    await session.commit()
    await session.refresh(data)
    return data


@router.delete("/{data_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_data(data_id: str, session: AsyncSession = Depends(get_session), role: Role = Depends(require_roles(Role.SUBSIDIARY, Role.HQ, Role.ADMIN)), entity_id: str | None = Depends(current_entity)):
    data = await get_financial_data(session, data_id)
    require_entity_scope(role, entity_id, data.company_id)
    if role == Role.SUBSIDIARY and data.is_submitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submitted data must be returned by HQ before deletion")
    fiscal_year = data.fiscal_year
    await session.delete(data)
    await session.commit()
    # Removing an approved row must drop it from the Dashboard cache.
    await rebuild_summaries(session, fiscal_year)
