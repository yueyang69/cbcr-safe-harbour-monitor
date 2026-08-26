"""Jurisdiction whitelist: no more free-text pollution like 'UK2' / 'TestReturn'."""

PAYLOAD = {
    "fiscal_year": 2025, "jurisdiction": "Japan", "currency": "EUR",
    "revenue": "15000000", "pbt": "1200000", "covered_taxes": "200000",
    "payroll": "3000000", "tangible_assets": "5000000",
}


async def test_list_jurisdictions_is_public_and_complete(client):
    response = await client.get("/api/v1/jurisdictions")
    assert response.status_code == 200
    jurisdictions = response.json()["jurisdictions"]
    assert "Japan" in jurisdictions
    assert "Germany" in jurisdictions
    assert "United States" in jurisdictions
    assert "EUR" not in jurisdictions


async def test_create_rejects_unknown_jurisdiction(client):
    company = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": "Junk Co"})
    company_id = company.json()["id"]
    response = await client.post("/api/v1/financial-data", headers={"X-User-Role": "hq"}, json={
        "company_id": company_id, **{**PAYLOAD, "jurisdiction": "TestReturn"},
    })
    assert response.status_code == 422  # pydantic validation error


async def test_quick_submit_rejects_unknown_jurisdiction(client):
    company = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": "Junk Co 2"})
    company_id = company.json()["id"]
    response = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json={
        "company_id": company_id, **{**PAYLOAD, "jurisdiction": "UK2"},
    })
    assert response.status_code == 422


async def test_alias_is_canonicalised_on_input(client):
    company = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": "Alias Co"})
    company_id = company.json()["id"]
    response = await client.post("/api/v1/financial-data/quick-submit", headers={"X-User-Role": "hq"}, json={
        "company_id": company_id, **{**PAYLOAD, "jurisdiction": "US"},
    })
    assert response.status_code == 200
    assert response.json()["jurisdiction"] == "United States"
