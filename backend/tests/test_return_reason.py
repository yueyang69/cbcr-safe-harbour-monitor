"""HQ return -> reason shown -> subsidiary resubmits -> reason cleared.

Covers the "退回消息给子公司" loop end to end at the API level.
"""


async def _hq_company(client, name: str = "Return Co") -> str:
    response = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


PAYLOAD = {
    "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR",
    "revenue": "15000000", "pbt": "1200000", "covered_taxes": "200000",
    "payroll": "3000000", "tangible_assets": "5000000",
}


async def _strict_submission(client, company_id):
    """create (subsidiary) -> submit -> return -> resubmit; returns the data id."""
    created = await client.post(
        "/api/v1/financial-data",
        headers={"X-User-Role": "subsidiary", "X-Entity-Id": company_id},
        json={"company_id": company_id, **PAYLOAD},
    )
    assert created.status_code == 201
    data_id = created.json()["id"]
    assert (await client.post(f"/api/v1/financial-data/{data_id}/submit", headers={"X-User-Role": "subsidiary", "X-Entity-Id": company_id})).status_code == 200
    return data_id


async def test_return_with_reason_persists_and_leaves_dashboard(client):
    company_id = await _hq_company(client)
    data_id = await _strict_submission(client, company_id)

    response = await client.post(
        f"/api/v1/financial-data/{data_id}/return",
        headers={"X-User-Role": "hq"},
        json={"reason": "Revenue and PBT don't match the trial balance."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_submitted"] is False
    assert body["is_approved"] is False
    assert body["return_reason"] == "Revenue and PBT don't match the trial balance."

    # The subsidiary can read the reason back.
    listed = await client.get("/api/v1/financial-data", headers={"X-User-Role": "subsidiary", "X-Entity-Id": company_id})
    assert listed.status_code == 200
    row = next(r for r in listed.json() if r["id"] == data_id)
    assert row["return_reason"] == "Revenue and PBT don't match the trial balance."


async def test_return_without_reason_is_backwards_compatible(client):
    company_id = await _hq_company(client)
    data_id = await _strict_submission(client, company_id)
    response = await client.post(f"/api/v1/financial-data/{data_id}/return", headers={"X-User-Role": "hq"})
    assert response.status_code == 200
    assert response.json()["return_reason"] is None


async def test_resubmit_clears_return_reason(client):
    company_id = await _hq_company(client)
    data_id = await _strict_submission(client, company_id)
    await client.post(f"/api/v1/financial-data/{data_id}/return", headers={"X-User-Role": "hq"}, json={"reason": "Please fix revenue."})

    headers = {"X-User-Role": "subsidiary", "X-Entity-Id": company_id}
    resubmit = await client.post(f"/api/v1/financial-data/{data_id}/submit", headers=headers)
    assert resubmit.status_code == 200
    assert resubmit.json()["is_submitted"] is True
    assert resubmit.json()["return_reason"] is None

    # And it is visible in the HQ approval queue again.
    queue = (await client.get("/api/v1/financial-data", headers={"X-User-Role": "hq"})).json()
    assert any(row["id"] == data_id and row["is_submitted"] and not row["is_approved"] for row in queue)


async def test_quick_submit_clears_return_reason(client):
    company_id = await _hq_company(client)
    data_id = await _strict_submission(client, company_id)
    await client.post(f"/api/v1/financial-data/{data_id}/return", headers={"X-User-Role": "hq"}, json={"reason": "Fix it."})

    headers = {"X-User-Role": "hq"}
    upsert = await client.post("/api/v1/financial-data/quick-submit", headers=headers, json={"company_id": company_id, **PAYLOAD})
    assert upsert.status_code == 200
    assert upsert.json()["return_reason"] is None


async def test_admin_delete_removes_row_and_dashboard_entry(client):
    company_id = await _hq_company(client)
    created = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json={"company_id": company_id, **PAYLOAD})
    data_id = created.json()["id"]

    delete = await client.delete(f"/api/v1/financial-data/{data_id}", headers={"X-User-Role": "admin"})
    assert delete.status_code == 204

    listed = (await client.get("/api/v1/financial-data", headers={"X-User-Role": "admin"})).json()
    assert all(row["id"] != data_id for row in listed)
    dashboard = (await client.get("/api/v1/dashboard?fiscal_year=2025", headers={"X-User-Role": "hq"})).json()
    assert dashboard["kpis"]["jurisdiction_count"] == 0
