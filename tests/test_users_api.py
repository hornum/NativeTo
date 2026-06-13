from httpx import AsyncClient

from tests.conftest import FakeRedis


async def test_get_me_returns_profile(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/users/me")
    assert response.status_code == 200

    data = response.json()
    assert data.get("username") == "testuser", response.json()
    assert "languages" in data, response.json()
    assert len(data.get("languages")) == 2, response.json()


async def test_get_me_unauthorized_fails(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401, response.json()


async def test_patch_me_updates_fields(auth_client: AsyncClient):
    await auth_client.patch("/api/v1/users/me", json={"username": "patchworks", "country": "US"})
    response = await auth_client.get("/api/v1/users/me")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data.get("username") == "patchworks", response.json()
    assert data.get("country") == "US", response.json()


async def test_patch_username_to_taken_fails(auth_client: AsyncClient, client: AsyncClient, auth_json_data):
    second_user = {**auth_json_data, "username": "testuser1", "email": "testuser1@example.com"}
    await client.post("/api/v1/auth/register", json=second_user)
    response = await auth_client.patch("/api/v1/users/me", json={"username": "testuser1"})

    assert response.status_code == 400, response.json()


async def test_add_language(auth_client: AsyncClient):
    await auth_client.post("/api/v1/users/me/languages", json={"language": "Spanish", "level": "intermediate"})
    response = await auth_client.get("/api/v1/users/me")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert len(data.get("languages")) == 3, response.json()


async def test_add_second_native_fails(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/v1/users/me/languages", json={"language": "Spanish", "level": "native"}
    )
    assert response.status_code == 400, response.json()


async def test_catalog_matches_languages(auth_client: AsyncClient, client: AsyncClient, auth_json_data):
    partner_match = {**auth_json_data, "username": "testuser1", "email": "testuser1@example.com",
                   "native_language": "Russian", "learning_language": "English"}
    await client.post("/api/v1/auth/register", json=partner_match)

    response = await auth_client.get("/api/v1/users/catalog")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert len(data) == 1, response.json()

    partner_nomatch = {**auth_json_data, "username": "testuser2", "email": "testuser2@example.com",
                   "native_language": "Korean", "learning_language": "Arabic"}
    await client.post("/api/v1/auth/register", json=partner_nomatch)

    response = await auth_client.get("/api/v1/users/catalog")
    data = response.json()
    assert len(data) == 1, response.json()


async def test_patch_name_is_free(auth_client: AsyncClient, client: AsyncClient, auth_json_data):
    user2 = {**auth_json_data, "username": "user2", "email": "user2@example.com", "name": "Anna"}
    await client.post("/api/v1/auth/register", json=user2)

    response = await auth_client.patch("/api/v1/users/me", json={"name": "Anna"})
    assert response.status_code == 200, response.json()
    assert response.json()["name"] == "Anna", response.json()


async def test_verify_flow(client: AsyncClient, fake_redis: FakeRedis, auth_json_data):
    await client.post("/api/v1/auth/register", json=auth_json_data)
    token = next(k.removeprefix("verify:") for k in fake_redis._storage if k.startswith("verify:"))
    response = await client.get(f"/api/v1/auth/verify?token={token}")

    assert response.status_code == 200, response.json()
    assert f"verify:{token}" not in fake_redis._storage, response.json()


async def test_verify_invalid_token_fails(client: AsyncClient):
    response = await client.get(f"/api/v1/auth/verify?token=invalid")
    assert response.status_code == 401, response.json()


async def test_verify_twice_fails(client: AsyncClient, fake_redis: FakeRedis, auth_json_data):
    await client.post("/api/v1/auth/register", json=auth_json_data)
    token = next(k.removeprefix("verify:") for k in fake_redis._storage if k.startswith("verify:"))

    response = await client.get(f"/api/v1/auth/verify?token={token}")
    assert response.status_code == 200, response.json()

    response = await client.get(f"/api/v1/auth/verify?token={token}")
    assert response.status_code == 401, response.json()
