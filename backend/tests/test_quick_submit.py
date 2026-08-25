"""MVP Scenario 1: HQ save -> auto-approve -> rebuild -> Dashboard shows it."""


async def _hq_company(client, name: str = "Quick Co") -> str:
    response = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


PAYLOAD = {
    "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR",
    "revenue": "15000000", "pbt": "1200000", "covered_taxes": "200000",
    "payroll": "3000000", "tangible_assets": "5000000",
}


async def test_quick_submit_approves_and_publishes_to_dashboard(client):
    company_id = await _hq_company(client)
    response = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json={"company_id": company_id, **PAYLOAD})
    assert response.status_code == 200
    body = response.json()
    assert body["is_submitted"] is True
    assert body["is_approved"] is True
    assert body["requires_manual_confirmation"] is False

    dashboard = (await client.get("/api/v1/dashboard?fiscal_year=2025", headers={"X-User-Role": "hq"})).json()
    assert dashboard["kpis"]["jurisdiction_count"] == 1
    assert dashboard["jurisdictions"][0]["jurisdiction"] == "Japan"


async def test_quick_submit_upserts_instead_of_409(client):
    company_id = await _hq_company(client)
    payload = {"company_id": company_id, **PAYLOAD}
    first = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json=payload)
    assert first.status_code == 200
    second = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json={**payload, "revenue": "16000000"})
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]  # same row, updated
    assert second.json()["revenue"] == "16000000.00"


async def test_quick_submit_rejects_non_eur_as_manual_confirmation(client):
    company_id = await _hq_company(client)
    response = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json={
        "company_id": company_id, **{**PAYLOAD, "currency": "USD"},
    })
    assert response.status_code == 200
    assert response.json()["requires_manual_confirmation"] is True


async def test_quick_submit_forbidden_for_subsidiary(client):
    company_id = await _hq_company(client)
    response = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "subsidiary", "X-Entity-Id": company_id}, json={"company_id": company_id, **PAYLOAD})
    assert response.status_code == 403


async def test_quick_submit_forbidden_for_reviewer(client):
    company_id = await _hq_company(client)
    response = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "reviewer"}, json={"company_id": company_id, **PAYLOAD})
    assert response.status_code == 403


async def test_two_entities_same_jurisdiction_aggregate_into_one_summary(client):
    """拍板 #4: entity 与 jurisdiction 分离 —— 集团下多个 entity/branch 最终按 jurisdiction 汇总为一条。"""
    headers = {"X-User-Role": "hq"}
    nl_a = (await client.post("/api/v1/companies", headers=headers, json={"name": "NL Entity A"})).json()["id"]
    nl_b = (await client.post("/api/v1/companies", headers=headers, json={"name": "NL Entity B"})).json()["id"]
    for company_id in (nl_a, nl_b):
        response = await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={
            "company_id": company_id, **{**PAYLOAD, "jurisdiction": "Netherlands", "revenue": "10000000"},
        })
        assert response.status_code == 200

    summaries = (await client.get("/api/v1/summaries?fiscal_year=2025", headers=headers)).json()
    nl = [s for s in summaries if s["jurisdiction"] == "Netherlands"]
    assert len(nl) == 1  # two entities roll up into ONE jurisdiction summary
    assert nl[0]["company_count"] == 2
    assert nl[0]["included_count"] == 2
    assert float(nl[0]["revenue"]) == 20000000.0  # summed across entities

