"""End-to-end demo flow: CSV batch-upload -> batch-commit -> batch-submit ->
HQ approve -> Dashboard. Mirrors the exact frontend request sequence so a
regression in the demo path fails loudly here."""

import io

DEMO_CSV = "entity_name,fiscal_year,currency,revenue,profit_before_tax,covered_taxes,payroll,tangible_assets\n" \
           "Japan,2026,EUR,8500000,1200000,450000,3200000,15000000\n" \
           "Germany,2026,EUR,4200000,380000,150000,1800000,8000000\n" \
           "Netherlands,2026,EUR,6700000,520000,210000,2800000,12000000\n"


async def test_demo_csv_flow_submit_approve_dashboard(client):
    # HQ creates the reporting entity
    r = await client.post("/api/v1/companies", headers={"X-User-Role": "hq"},
                          json={"name": "Demo Group", "country": "SG", "entity_type": "subsidiary"})
    assert r.status_code == 201, r.text
    company_id = r.json()["id"]
    sub = {"X-User-Role": "subsidiary", "X-Entity-Id": company_id}

    # 1. Subsidiary uploads the standard demo CSV -> all columns auto-map
    up = await client.post("/api/v1/financial-data/batch-upload", headers=sub,
                           files={"file": ("demo.csv", io.BytesIO(DEMO_CSV.encode("utf-8")), "text/csv")},
                           data={"fiscal_year": "2026", "company_id": company_id})
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["total_rows"] == 3
    assert all(col["mapped_field"] for col in body["columns"]), [c["csv_name"] for c in body["columns"] if not c["mapped_field"]]

    # 2. Commit (build rows exactly like the frontend buildRows())
    rows = []
    for raw in body["rows"]:
        row = {"jurisdiction": "", "currency": "EUR", "revenue": None, "pbt": None,
               "covered_taxes": None, "payroll": None, "tangible_assets": None}
        for col in body["columns"]:
            field = col["mapped_field"]
            if not field:
                continue
            value = str(raw.get(col["csv_name"], "")).strip()
            if field == "jurisdiction":
                row["jurisdiction"] = value
            elif field == "currency":
                row["currency"] = value.upper()
            elif field in ("revenue", "pbt", "covered_taxes", "payroll", "tangible_assets"):
                row[field] = float(value.replace(",", "")) if value else None
        rows.append(row)
    cc = await client.post("/api/v1/financial-data/batch-commit", headers=sub,
                           json={"company_id": company_id, "fiscal_year": 2026, "rows": rows})
    assert cc.status_code == 200, cc.text
    assert cc.json()["success_count"] == 3

    # 3. Whole batch reaches HQ with one click
    bs = await client.post("/api/v1/financial-data/batch-submit", headers=sub,
                           json={"company_id": company_id, "fiscal_year": 2026})
    assert bs.status_code == 200, bs.text
    assert bs.json()["submitted_count"] == 3

    # 4. HQ sees 3 pending and approves them
    lst = await client.get("/api/v1/financial-data", headers={"X-User-Role": "hq"})
    pending = [d for d in lst.json() if d["is_submitted"] and not d["is_approved"]]
    assert len(pending) == 3
    for d in pending:
        ap = await client.post(f"/api/v1/financial-data/{d['id']}/approve", headers={"X-User-Role": "hq"})
        assert ap.status_code == 200, ap.text

    # 5. Dashboard shows the 3 jurisdictions
    dash = await client.get("/api/v1/dashboard", headers={"X-User-Role": "hq"})
    assert dash.status_code == 200, dash.text
    data = dash.json()
    assert data["kpis"]["jurisdiction_count"] == 3
    assert sorted(j["jurisdiction"] for j in data["jurisdictions"]) == ["Germany", "Japan", "Netherlands"]
