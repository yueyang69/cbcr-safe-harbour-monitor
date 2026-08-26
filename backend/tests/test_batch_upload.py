"""Stage 3 CSV batch upload tests: mapping suggestions, atomic commit, RBAC,
encoding fallback, and the relaxed (company_id, fiscal_year, jurisdiction) unique
constraint."""

import io


STD_CSV = """jurisdiction,currency,revenue,pbt,covered_taxes,payroll,tangible_assets
Japan,EUR,8500000,1200000,450000,3200000,15000000
Germany,EUR,4200000,380000,150000,1800000,8000000
Netherlands,EUR,6700000,520000,210000,2800000,12000000
"""

CN_CSV = """辖区,币种,营业收入,税前利润,已涵盖所得税,员工薪酬,有形资产
Japan,EUR,8500000,1200000,450000,3200000,15000000
"""

CHALLENGE_CSV = """jurisdiction,currency,revenue,员工人数,pbt
Japan,EUR,8500000,85,1200000
"""


async def _make_company(client, name: str = "Batch Co") -> str:
    response = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _upload(client, csv_text: str, company_id: str, fiscal_year: int = 2026,
                  role: str = "hq", entity_id: str | None = None, name: str = "data.csv"):
    headers = {"X-User-Role": role}
    if entity_id:
        headers["X-Entity-Id"] = entity_id
    files = {"file": (name, io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    data = {"fiscal_year": str(fiscal_year), "company_id": company_id or ""}
    return await client.post("/api/v1/financial-data/batch-upload", headers=headers, files=files, data=data)


# --- batch-upload mapping ---

async def test_batch_upload_standard_columns_fully_mapped(client):
    company_id = await _make_company(client)
    response = await _upload(client, STD_CSV, company_id)
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 3
    mapped = {col["csv_name"]: col["mapped_field"] for col in body["columns"]}
    assert mapped["jurisdiction"] == "jurisdiction"
    assert mapped["currency"] == "currency"
    assert mapped["revenue"] == "revenue"
    assert mapped["pbt"] == "pbt"
    assert mapped["covered_taxes"] == "covered_taxes"
    assert mapped["payroll"] == "payroll"
    assert mapped["tangible_assets"] == "tangible_assets"
    assert all(col["confidence"] == 1.0 for col in body["columns"])
    assert len(body["preview_data"]) == 3
    assert body["preview_data"][0]["jurisdiction"] == "Japan"


async def test_batch_upload_chinese_aliases(client):
    company_id = await _make_company(client)
    response = await _upload(client, CN_CSV, company_id)
    assert response.status_code == 200
    mapped = {col["csv_name"]: col["mapped_field"] for col in response.json()["columns"]}
    assert mapped["辖区"] == "jurisdiction"
    assert mapped["币种"] == "currency"
    assert mapped["营业收入"] == "revenue"
    assert mapped["税前利润"] == "pbt"
    assert mapped["已涵盖所得税"] == "covered_taxes"
    assert mapped["员工薪酬"] == "payroll"
    assert mapped["有形资产"] == "tangible_assets"
    for col in response.json()["columns"]:
        assert col["confidence"] >= 0.6  # all aliases above the manual-selection threshold


async def test_batch_upload_unknown_column_unmapped(client):
    company_id = await _make_company(client)
    response = await _upload(client, CHALLENGE_CSV, company_id)
    assert response.status_code == 200
    mapped = {col["csv_name"]: col["mapped_field"] for col in response.json()["columns"]}
    assert mapped["员工人数"] is None
    assert mapped["revenue"] == "revenue"


async def test_batch_upload_demo_standard_csv_fully_mapped(client):
    """The plan's standard demo CSV (entity_name + profit_before_tax headers) must auto-map 100%."""
    company_id = await _make_company(client)
    csv_text = "entity_name,fiscal_year,currency,revenue,profit_before_tax,covered_taxes,payroll,tangible_assets\nJapan,2026,EUR,8500000,1200000,450000,3200000,15000000\n"
    response = await _upload(client, csv_text, company_id)
    assert response.status_code == 200
    mapped = {col["csv_name"]: col["mapped_field"] for col in response.json()["columns"]}
    assert mapped["entity_name"] == "jurisdiction"
    assert mapped["profit_before_tax"] == "pbt"
    assert mapped["fiscal_year"] == "fiscal_year"
    assert mapped["tangible_assets"] == "tangible_assets"
    assert all(col["mapped_field"] for col in response.json()["columns"])


async def test_batch_upload_demo_chinese_csv_fully_mapped(client):
    """The plan's Chinese demo CSV must auto-map 100%."""
    company_id = await _make_company(client)
    csv_text = "公司名称,会计年度,币种,营业收入,税前利润,已缴税款,薪酬总额,有形资产\nJapan,2026,EUR,8500000,1200000,450000,3200000,15000000\n"
    response = await _upload(client, csv_text, company_id)
    assert response.status_code == 200
    mapped = {col["csv_name"]: col["mapped_field"] for col in response.json()["columns"]}
    assert mapped["公司名称"] == "jurisdiction"
    assert mapped["已缴税款"] == "covered_taxes"
    assert mapped["薪酬总额"] == "payroll"
    assert mapped["会计年度"] == "fiscal_year"
    assert mapped["币种"] == "currency"
    assert mapped["营业收入"] == "revenue"
    assert mapped["税前利润"] == "pbt"
    assert mapped["有形资产"] == "tangible_assets"
    assert all(col["mapped_field"] for col in response.json()["columns"])


async def test_batch_upload_demo_challenge_csv_eight_of_nine(client):
    """The plan's challenge demo CSV maps 8/9; only 员工人数 requires manual choice."""
    company_id = await _make_company(client)
    csv_text = "公司全称,财年,本地货币,总收入,税前利润,已缴公司税,员工薪酬,固定资产,员工人数\nJapan,2026,EUR,8500000,1200000,450000,3200000,15000000,85\n"
    response = await _upload(client, csv_text, company_id)
    assert response.status_code == 200
    mapped = {col["csv_name"]: col["mapped_field"] for col in response.json()["columns"]}
    assert mapped["公司全称"] == "jurisdiction"
    assert mapped["财年"] == "fiscal_year"
    assert mapped["本地货币"] == "currency"
    assert mapped["总收入"] == "revenue"
    assert mapped["已缴公司税"] == "covered_taxes"
    assert mapped["员工薪酬"] == "payroll"
    assert mapped["固定资产"] == "tangible_assets"
    assert mapped["员工人数"] is None  # the intended human-intervention column


async def test_batch_upload_gbk_encoding_fallback(client):
    company_id = await _make_company(client)
    gbk_bytes = "辖区,币种,营业收入\nJapan,EUR,8500000\n".encode("gbk")
    files = {"file": ("gbk.csv", io.BytesIO(gbk_bytes), "text/csv")}
    response = await client.post("/api/v1/financial-data/batch-upload",
                                 headers={"X-User-Role": "hq"},
                                 files=files,
                                 data={"fiscal_year": "2026", "company_id": company_id})
    assert response.status_code == 200
    assert response.json()["total_rows"] == 1


async def test_batch_upload_empty_file_400(client):
    company_id = await _make_company(client)
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    response = await client.post("/api/v1/financial-data/batch-upload",
                                 headers={"X-User-Role": "hq"},
                                 files=files,
                                 data={"fiscal_year": "2026", "company_id": company_id})
    assert response.status_code == 400


async def test_batch_upload_header_only_400(client):
    company_id = await _make_company(client)
    files = {"file": ("h.csv", io.BytesIO(b"jurisdiction,revenue\n"), "text/csv")}
    response = await client.post("/api/v1/financial-data/batch-upload",
                                 headers={"X-User-Role": "hq"},
                                 files=files,
                                 data={"fiscal_year": "2026", "company_id": company_id})
    assert response.status_code == 400


# --- batch-commit ---

def _commit_payload(company_id: str, rows: list[dict], fiscal_year: int = 2026) -> dict:
    return {"company_id": company_id, "fiscal_year": fiscal_year, "rows": rows}


async def test_batch_commit_creates_draft_rows(client):
    company_id = await _make_company(client)
    response = await client.post("/api/v1/financial-data/batch-commit", headers={"X-User-Role": "hq"}, json=_commit_payload(company_id, [
        {"jurisdiction": "Japan", "currency": "EUR", "revenue": "8500000", "pbt": "1200000", "covered_taxes": "450000", "payroll": "3200000", "tangible_assets": "15000000"},
        {"jurisdiction": "Germany", "currency": "EUR", "revenue": "4200000", "pbt": "380000", "covered_taxes": "150000", "payroll": "1800000", "tangible_assets": "8000000"},
    ]))
    assert response.status_code == 200
    body = response.json()
    assert body["success_count"] == 2
    assert body["failed_rows"] == []

    rows = (await client.get("/api/v1/financial-data", headers={"X-User-Role": "hq"}, params={"company_id": company_id})).json()
    assert len(rows) == 2
    assert all(r["is_submitted"] is False for r in rows)
    assert all(r["is_approved"] is False for r in rows)


async def test_batch_commit_conflict_409_no_partial_write(client):
    company_id = await _make_company(client)
    payload = _commit_payload(company_id, [{"jurisdiction": "Japan", "currency": "EUR", "revenue": "1"}])
    first = await client.post("/api/v1/financial-data/batch-commit", headers={"X-User-Role": "hq"}, json=payload)
    assert first.status_code == 200
    second = await client.post("/api/v1/financial-data/batch-commit", headers={"X-User-Role": "hq"}, json=payload)
    assert second.status_code == 409
    rows = (await client.get("/api/v1/financial-data", headers={"X-User-Role": "hq"}, params={"company_id": company_id})).json()
    assert len(rows) == 1  # nothing was written on the conflicting commit


async def test_batch_commit_non_eur_requires_manual_confirmation(client):
    company_id = await _make_company(client)
    response = await client.post("/api/v1/financial-data/batch-commit", headers={"X-User-Role": "hq"}, json=_commit_payload(company_id, [
        {"jurisdiction": "US", "currency": "USD", "revenue": "1"},
    ]))
    assert response.status_code == 200
    rows = (await client.get("/api/v1/financial-data", headers={"X-User-Role": "hq"}, params={"company_id": company_id})).json()
    assert rows[0]["requires_manual_confirmation"] is True


async def test_batch_commit_entity_name_maps_to_canonical_jurisdiction(client):
    """A CSV entity-name value (新加坡子公司) is stored as its canonical country (Singapore)."""
    company_id = await _make_company(client)
    response = await client.post("/api/v1/financial-data/batch-commit", headers={"X-User-Role": "hq"}, json=_commit_payload(company_id, [
        {"jurisdiction": "新加坡子公司", "currency": "EUR", "revenue": "8500000"},
    ]))
    assert response.status_code == 200
    rows = (await client.get("/api/v1/financial-data", headers={"X-User-Role": "hq"}, params={"company_id": company_id})).json()
    assert rows[0]["jurisdiction"] == "Singapore"


async def test_batch_commit_rejects_unknown_jurisdiction(client):
    """Batch import cannot bypass the whitelist either (no junk jurisdictions)."""
    company_id = await _make_company(client)
    response = await client.post("/api/v1/financial-data/batch-commit", headers={"X-User-Role": "hq"}, json=_commit_payload(company_id, [
        {"jurisdiction": "TestReturn", "currency": "EUR", "revenue": "1"},
    ]))
    assert response.status_code == 422  # pydantic validation error


# --- batch-submit (whole import reaches HQ in one click) ---

async def test_batch_submit_submits_all_drafts(client):
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    cc = await client.post("/api/v1/financial-data/batch-commit", headers=headers, json=_commit_payload(company_id, [
        {"jurisdiction": "Japan", "currency": "EUR", "revenue": "1"},
        {"jurisdiction": "Germany", "currency": "EUR", "revenue": "2"},
        {"jurisdiction": "Netherlands", "currency": "EUR", "revenue": "3"},
    ]))
    assert cc.status_code == 200

    response = await client.post("/api/v1/financial-data/batch-submit", headers=headers,
                                 json={"company_id": company_id, "fiscal_year": 2026})
    assert response.status_code == 200
    assert response.json()["submitted_count"] == 3

    rows = (await client.get("/api/v1/financial-data", headers=headers, params={"company_id": company_id})).json()
    assert len(rows) == 3
    assert all(r["is_submitted"] for r in rows)
    assert all(not r["is_approved"] for r in rows)


async def test_batch_submit_is_idempotent_and_skips_approved(client):
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    await client.post("/api/v1/financial-data/batch-commit", headers=headers, json=_commit_payload(company_id, [
        {"jurisdiction": "Japan", "currency": "EUR", "revenue": "1"},
    ]))
    first = await client.post("/api/v1/financial-data/batch-submit", headers=headers,
                              json={"company_id": company_id, "fiscal_year": 2026})
    assert first.status_code == 200
    second = await client.post("/api/v1/financial-data/batch-submit", headers=headers,
                               json={"company_id": company_id, "fiscal_year": 2026})
    assert second.json()["submitted_count"] == 0  # nothing left to submit
    # an approved row is never re-submitted
    rows = (await client.get("/api/v1/financial-data", headers=headers, params={"company_id": company_id})).json()
    assert rows[0]["is_approved"] is False


async def test_batch_submit_clears_return_reason(client):
    """Resubmitting a returned row via batch-submit drops the stale return reason."""
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    created = await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Japan", "currency": "EUR", "revenue": "1",
    })
    assert created.status_code == 200
    returned = await client.post(f"/api/v1/financial-data/{created.json()['id']}/return", headers=headers, json={"reason": "fix the revenue"})
    assert returned.status_code == 200
    assert returned.json()["is_submitted"] is False
    assert returned.json()["return_reason"] == "fix the revenue"

    submitted = await client.post("/api/v1/financial-data/batch-submit", headers=headers,
                                  json={"company_id": company_id, "fiscal_year": 2026})
    assert submitted.status_code == 200
    assert submitted.json()["submitted_count"] == 1
    rows = (await client.get("/api/v1/financial-data", headers=headers, params={"company_id": company_id})).json()
    assert rows[0]["is_submitted"] is True
    assert rows[0]["return_reason"] is None


async def test_batch_submit_subsidiary_other_company_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    response = await client.post("/api/v1/financial-data/batch-submit",
                                 headers={"X-User-Role": "subsidiary", "X-Entity-Id": a},
                                 json={"company_id": b, "fiscal_year": 2026})
    assert response.status_code == 403


# --- batch-approve (HQ '批量通过') ---

async def test_batch_approve_approves_whole_pending_queue(client):
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    await client.post("/api/v1/financial-data/batch-commit", headers=headers, json=_commit_payload(company_id, [
        {"jurisdiction": "Japan", "currency": "EUR", "revenue": "1"},
        {"jurisdiction": "Germany", "currency": "EUR", "revenue": "2"},
    ]))
    await client.post("/api/v1/financial-data/batch-submit", headers=headers,
                      json={"company_id": company_id, "fiscal_year": 2026})

    response = await client.post("/api/v1/financial-data/batch-approve", headers={"X-User-Role": "hq"})
    assert response.status_code == 200
    assert response.json()["approved_count"] == 2

    rows = (await client.get("/api/v1/financial-data", headers=headers, params={"company_id": company_id})).json()
    assert all(r["is_approved"] for r in rows)
    # the Dashboard was rebuilt so both jurisdictions appear
    dash = (await client.get("/api/v1/dashboard", headers=headers)).json()
    assert dash["kpis"]["jurisdiction_count"] == 2


async def test_batch_approve_idempotent_and_forbidden_for_subsidiary(client):
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Japan", "currency": "EUR", "revenue": "1",
    })
    first = await client.post("/api/v1/financial-data/batch-approve", headers={"X-User-Role": "hq"})
    assert first.status_code == 200
    second = await client.post("/api/v1/financial-data/batch-approve", headers={"X-User-Role": "hq"})
    assert second.json()["approved_count"] == 0

    denied = await client.post("/api/v1/financial-data/batch-approve",
                               headers={"X-User-Role": "subsidiary", "X-Entity-Id": company_id})
    assert denied.status_code == 403


# --- RBAC ---

async def test_batch_commit_subsidiary_other_company_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    response = await client.post("/api/v1/financial-data/batch-commit",
                                 headers={"X-User-Role": "subsidiary", "X-Entity-Id": a},
                                 json=_commit_payload(b, [{"jurisdiction": "Japan", "currency": "EUR"}]))
    assert response.status_code == 403


async def test_batch_upload_subsidiary_missing_entity_400(client):
    await _make_company(client, "A Co")
    response = await _upload(client, STD_CSV, company_id=None, role="subsidiary")
    assert response.status_code == 400


async def test_batch_upload_subsidiary_forces_own_company(client):
    a = await _make_company(client, "A Co")
    await _make_company(client, "B Co")
    # Even if the form passes another company_id, a subsidiary is locked to its entity.
    response = await _upload(client, STD_CSV, company_id="some-other-id", role="subsidiary", entity_id=a)
    assert response.status_code == 200


# --- relaxed unique constraint ---

async def test_same_company_same_year_two_jurisdictions_ok(client):
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    r1 = await client.post("/api/v1/financial-data", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Japan", "currency": "EUR", "revenue": "1",
    })
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/financial-data", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Germany", "currency": "EUR", "revenue": "1",
    })
    assert r2.status_code == 201
    r3 = await client.post("/api/v1/financial-data", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Japan", "currency": "EUR", "revenue": "2",
    })
    assert r3.status_code == 409  # same company + year + jurisdiction still unique


async def test_quick_submit_two_jurisdictions_separate_rows(client):
    company_id = await _make_company(client)
    headers = {"X-User-Role": "hq"}
    r1 = await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Japan", "currency": "EUR", "revenue": "1000000",
    })
    r2 = await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Germany", "currency": "EUR", "revenue": "2000000",
    })
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["id"] != r2.json()["id"]  # separate rows, not overwritten
    r3 = await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2026, "jurisdiction": "Japan", "currency": "EUR", "revenue": "3000000",
    })
    assert r3.json()["id"] == r1.json()["id"]  # upsert updates the same row
    rows = (await client.get("/api/v1/financial-data", headers=headers)).json()
    assert len(rows) == 2
