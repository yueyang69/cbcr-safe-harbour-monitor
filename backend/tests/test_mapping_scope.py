"""拍板 #3: Mapping 作用域 —— 子公司确认映射只作用于本次上传，不写全局规则。"""
from sqlalchemy import select
from app.models import MappingRule


async def test_subsidiary_confirm_does_not_write_global_mapping(client, query_db):
    a = (await client.post("/api/v1/companies", headers={"X-User-Role": "hq"}, json={"name": "A Co"})).json()["id"]
    headers = {"X-User-Role": "subsidiary", "X-Entity-Id": a}
    response = await client.post("/api/v1/mapping/confirm", headers=headers, json={
        "mappings": [{"source_field": "全年税前利润", "target_field": "pbt", "confidence": "0.98"}]
    })
    assert response.status_code == 200  # acknowledged for this upload
    async with query_db() as session:
        rules = list((await session.scalars(select(MappingRule))).all())
    assert rules == []  # subsidiary must not touch the global mapping dictionary


async def test_hq_confirm_persists_global_mapping(client, query_db):
    response = await client.post("/api/v1/mapping/confirm", headers={"X-User-Role": "hq"}, json={
        "mappings": [{"source_field": "全年税前利润", "target_field": "pbt", "confidence": "0.98"}]
    })
    assert response.status_code == 200
    async with query_db() as session:
        rules = list((await session.scalars(select(MappingRule))).all())
    assert len(rules) == 1
    assert rules[0].source_field == "全年税前利润"
    assert rules[0].target_field == "pbt"
    assert rules[0].confirmed_by == "hq"
    assert rules[0].confirmed_by_user is True


async def test_hq_reconfirm_is_idempotent(client, query_db):
    """Re-confirming the same rule must update it, not hit the unique constraint."""
    headers = {"X-User-Role": "hq"}
    payload = {"mappings": [{"source_field": "全年税前利润", "target_field": "pbt", "confidence": "0.98"}]}
    first = await client.post("/api/v1/mapping/confirm", headers=headers, json=payload)
    assert first.status_code == 200
    second = await client.post("/api/v1/mapping/confirm", headers=headers, json=payload)
    assert second.status_code == 200
    async with query_db() as session:
        rules = list((await session.scalars(select(MappingRule))).all())
    assert len(rules) == 1  # still a single row, not a unique-constraint 500


async def test_admin_confirm_persists_global_mapping(client, query_db):
    response = await client.post("/api/v1/mapping/confirm", headers={"X-User-Role": "admin"}, json={
        "mappings": [{"source_field": "收入", "target_field": "revenue", "confidence": "0.85"}]
    })
    assert response.status_code == 200
    async with query_db() as session:
        rules = list((await session.scalars(select(MappingRule))).all())
    assert len(rules) == 1
    assert rules[0].confirmed_by == "admin"


async def test_reviewer_cannot_confirm_mapping(client):
    response = await client.post("/api/v1/mapping/confirm", headers={"X-User-Role": "reviewer"}, json={
        "mappings": [{"source_field": "收入", "target_field": "revenue", "confidence": "0.98"}]
    })
    assert response.status_code == 403
