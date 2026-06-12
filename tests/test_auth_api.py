from httpx import AsyncClient


async def test_register_returns_tokens(client: AsyncClient, auth_json_data):
    response = await client.post(
        "/api/v1/auth/register",
        json=auth_json_data,
    )

    assert response.status_code == 200, response.json()

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user_id" in data


async def test_register_duplicate_fails(client: AsyncClient, auth_json_data):
    await client.post(
        "/api/v1/auth/register",
        json=auth_json_data,
    )
    response = await client.post(
        "/api/v1/auth/register",
        json=auth_json_data,
    )

    assert response.status_code == 400, response.json()


async def test_login_returns_tokens(client: AsyncClient, auth_json_data):
    await client.post("/api/v1/auth/register", json=auth_json_data)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": auth_json_data["username"], "password": auth_json_data["password"]})

    assert response.status_code == 200, response.json()
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_wrong_password_fails(client: AsyncClient, auth_json_data):
    await client.post("/api/v1/auth/register", json=auth_json_data)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": auth_json_data["username"], "password": "wrong"})

    assert response.status_code == 401, response.json()



async def test_refresh_rotates(client: AsyncClient, auth_json_data):
    response = await client.post("/api/v1/auth/register", json=auth_json_data)

    assert response.status_code == 200, response.json()
    data = response.json()

    await client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})

    assert response.status_code == 401, response.json()
