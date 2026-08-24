async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_hq_flow_builds_warning_dashboard(client):
    headers = {"X-User-Role": "hq"}
    company_response = await client.post("/api/v1/companies", headers=headers, json={"name": "Demo Co", "country": "DE"})
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    data_response = await client.post("/api/v1/financial-data", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2025, "jurisdiction": "Germany", "currency": "EUR",
        "revenue": "20000000", "pbt": "2000000", "covered_taxes": "0", "payroll": "0", "tangible_assets": "0",
    })
    assert data_response.status_code == 201
    data_id = data_response.json()["id"]
    assert (await client.post(f"/api/v1/financial-data/{data_id}/submit", headers=headers)).status_code == 200
    assert (await client.post(f"/api/v1/financial-data/{data_id}/approve", headers=headers)).status_code == 200
    rebuild = await client.post("/api/v1/summaries/rebuild?fiscal_year=2025", headers=headers)
    assert rebuild.status_code == 200
    assert rebuild.json()[0]["status"] == "WARNING"
    dashboard = (await client.get("/api/v1/dashboard?fiscal_year=2025", headers=headers)).json()
    assert dashboard["kpis"]["warning_count"] == 1
    assert "top_up_tax" not in str(dashboard)


async def test_non_eur_requires_manual_confirmation(client):
    headers = {"X-User-Role": "hq"}
    company_id = (await client.post("/api/v1/companies", headers=headers, json={"name": "USD Co"})).json()["id"]
    result = await client.post("/api/v1/financial-data", headers=headers, json={
        "company_id": company_id, "fiscal_year": 2025, "jurisdiction": "US", "currency": "USD",
        "revenue": "1", "pbt": "1", "covered_taxes": "1", "payroll": "1", "tangible_assets": "1",
    })
    assert result.status_code == 201
    assert result.json()["requires_manual_confirmation"] is True


async def test_reviewer_cannot_confirm_mapping(client):
    response = await client.post("/api/v1/mapping/confirm", headers={"X-User-Role": "reviewer"}, json={
        "mappings": [{"source_field": "收入", "target_field": "revenue", "confidence": "0.98"}]
    })
    assert response.status_code == 403
