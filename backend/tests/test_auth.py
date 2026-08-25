"""Demo-level admin login (POST /auth/login)."""


async def test_login_with_valid_admin_credentials(client):
    response = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    assert response.json() == {"role": "admin", "username": "admin"}


async def test_login_rejects_wrong_password(client):
    response = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


async def test_login_rejects_unknown_user(client):
    response = await client.post("/api/v1/auth/login", json={"username": "intruder", "password": "admin123"})
    assert response.status_code == 401
