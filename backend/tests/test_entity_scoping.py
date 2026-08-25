"""RBAC two-layer tests: subsidiary is scoped to exactly one entity (X-Entity-Id)."""


async def _make_company(client, name: str) -> str:
    response = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _make_data(client, company_id: str, jurisdiction: str = "Japan", fiscal_year: int = 2025) -> str:
    response = await client.post("/api/v1/financial-data", headers={"X-User-Role": "hq"}, json={
        "company_id": company_id, "fiscal_year": fiscal_year, "jurisdiction": jurisdiction, "currency": "EUR",
        "revenue": "20000000", "pbt": "2000000", "covered_taxes": "200000", "payroll": "1000000", "tangible_assets": "5000000",
    })
    assert response.status_code == 201
    return response.json()["id"]


def _sub(entity_id: str) -> dict:
    return {"X-User-Role": "subsidiary", "X-Entity-Id": entity_id}


# --- GET /companies scope ---

async def test_subsidiary_lists_only_own_company(client):
    a = await _make_company(client, "A Co")
    await _make_company(client, "B Co")
    response = await client.get("/api/v1/companies", headers=_sub(a))
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [a]


async def test_subsidiary_list_companies_missing_entity_400(client):
    await _make_company(client, "A Co")
    response = await client.get("/api/v1/companies", headers={"X-User-Role": "subsidiary"})
    assert response.status_code == 400


async def test_hq_lists_all_companies(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    response = await client.get("/api/v1/companies", headers={"X-User-Role": "hq"})
    assert response.status_code == 200
    assert {a, b} <= {item["id"] for item in response.json()}


# --- create ---

async def test_subsidiary_create_own_ok(client):
    a = await _make_company(client, "A Co")
    response = await client.post("/api/v1/financial-data", headers=_sub(a), json={
        "company_id": a, "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR", "revenue": "20000000",
    })
    assert response.status_code == 201


async def test_subsidiary_create_other_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    response = await client.post("/api/v1/financial-data", headers=_sub(a), json={
        "company_id": b, "fiscal_year": 2025, "jurisdiction": "Germany", "currency": "EUR",
    })
    assert response.status_code == 403


async def test_subsidiary_create_missing_entity_400(client):
    a = await _make_company(client, "A Co")
    response = await client.post("/api/v1/financial-data", headers={"X-User-Role": "subsidiary"}, json={
        "company_id": a, "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR",
    })
    assert response.status_code == 400


# --- list ---

async def test_subsidiary_lists_only_own_data(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    a_data = await _make_data(client, a)
    await _make_data(client, b, jurisdiction="Germany")
    response = await client.get("/api/v1/financial-data", headers=_sub(a))
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [a_data]


async def test_subsidiary_list_other_company_id_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    await _make_data(client, b, jurisdiction="Germany")
    response = await client.get("/api/v1/financial-data", headers=_sub(a), params={"company_id": b})
    assert response.status_code == 403


# --- submit ---

async def test_subsidiary_submit_other_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    b_data = await _make_data(client, b, jurisdiction="Germany")
    response = await client.post(f"/api/v1/financial-data/{b_data}/submit", headers=_sub(a))
    assert response.status_code == 403


# --- return + update flow ---

async def test_hq_return_then_subsidiary_edits(client):
    a = await _make_company(client, "A Co")
    data_id = await _make_data(client, a)
    await client.post(f"/api/v1/financial-data/{data_id}/submit", headers={"X-User-Role": "hq"})

    # Submitted data cannot be edited by the subsidiary until HQ returns it.
    put = await client.put(f"/api/v1/financial-data/{data_id}", headers=_sub(a), json={
        "company_id": a, "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR", "revenue": "21000000",
    })
    assert put.status_code == 403

    returned = await client.post(f"/api/v1/financial-data/{data_id}/return", headers={"X-User-Role": "hq"})
    assert returned.status_code == 200
    assert returned.json()["is_submitted"] is False
    assert returned.json()["is_approved"] is False

    put = await client.put(f"/api/v1/financial-data/{data_id}", headers=_sub(a), json={
        "company_id": a, "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR", "revenue": "21000000",
    })
    assert put.status_code == 200
    assert put.json()["revenue"] == "21000000.00"


async def test_subsidiary_update_own_unsubmitted_ok(client):
    a = await _make_company(client, "A Co")
    data_id = await _make_data(client, a)
    put = await client.put(f"/api/v1/financial-data/{data_id}", headers=_sub(a), json={
        "company_id": a, "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR", "revenue": "21000000",
    })
    assert put.status_code == 200
    assert put.json()["revenue"] == "21000000.00"


async def test_subsidiary_update_other_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    b_data = await _make_data(client, b, jurisdiction="Germany")
    put = await client.put(f"/api/v1/financial-data/{b_data}", headers=_sub(a), json={
        "company_id": b, "fiscal_year": 2025, "jurisdiction": "Germany", "currency": "EUR",
    })
    assert put.status_code == 403


async def test_update_duplicate_409(client):
    a = await _make_company(client, "A Co")
    await _make_data(client, a, fiscal_year=2025)
    data_id = await _make_data(client, a, fiscal_year=2026)
    put = await client.put(f"/api/v1/financial-data/{data_id}", headers={"X-User-Role": "hq"}, json={
        "company_id": a, "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR",
    })
    assert put.status_code == 409


# --- delete ---

async def test_subsidiary_delete_own_unsubmitted_ok(client):
    a = await _make_company(client, "A Co")
    data_id = await _make_data(client, a)
    response = await client.delete(f"/api/v1/financial-data/{data_id}", headers=_sub(a))
    assert response.status_code == 204


async def test_subsidiary_delete_own_submitted_403(client):
    a = await _make_company(client, "A Co")
    data_id = await _make_data(client, a)
    await client.post(f"/api/v1/financial-data/{data_id}/submit", headers={"X-User-Role": "hq"})
    response = await client.delete(f"/api/v1/financial-data/{data_id}", headers=_sub(a))
    assert response.status_code == 403


async def test_subsidiary_delete_other_403(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")
    b_data = await _make_data(client, b, jurisdiction="Germany")
    response = await client.delete(f"/api/v1/financial-data/{b_data}", headers=_sub(a))
    assert response.status_code == 403


# --- mapping ---

async def test_subsidiary_can_suggest_and_confirm_mapping(client):
    a = await _make_company(client, "A Co")
    suggest = await client.post("/api/v1/mapping/suggest", headers=_sub(a), json={"source_fields": ["全年税前利润"]})
    assert suggest.status_code == 200
    confirm = await client.post("/api/v1/mapping/confirm", headers=_sub(a), json={
        "mappings": [{"source_field": "全年税前利润", "target_field": "pbt", "confidence": "0.98"}]
    })
    assert confirm.status_code == 200


# --- AI scope ---

async def test_subsidiary_ai_scoped_to_own_entity(client):
    a = await _make_company(client, "A Co")
    b = await _make_company(client, "B Co")

    anomaly = await client.post("/api/v1/ai/anomaly-detection", headers=_sub(a), json={
        "company_id": b, "fiscal_year": 2025, "jurisdiction": "Germany",
    })
    assert anomaly.status_code == 403

    missing = await client.post("/api/v1/ai/suggest-missing", headers=_sub(a), json={
        "company_id": b, "field_name": "tangible_assets",
    })
    assert missing.status_code == 403

    ok = await client.post("/api/v1/ai/suggest-missing", headers=_sub(a), json={
        "company_id": a, "field_name": "tangible_assets",
    })
    assert ok.status_code == 200
