import pytest
import pytest_asyncio
from passlib.context import CryptContext
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool.impl import NullPool

from app.main import app
from app.db.session import get_db, Base
from app.service import auth as auth_service

fast_pwd_context = CryptContext(schemes=["md5_crypt"])

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/nativeto_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
test_session_maker = async_sessionmaker(
    bind=test_engine, expire_on_commit=False
)


async def override_get_db():
    async with test_session_maker() as session:
        yield session


class FakeRedis:
    def __init__(self):
        self._storage = {}

    async def set(self, key, value, ex=None):
        self._storage[key] = str(value)

    async def get(self, key):
        return self._storage.get(key)

    async def delete(self, key):
        self._storage.pop(key, None)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(auth_service, "redis_client", fake)
    monkeypatch.setattr(auth_service.send_verification_email, "delay", lambda *args, **kwargs: None)

    return fake


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    monkeypatch.setattr(auth_service, "pwd_context", fast_pwd_context)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def auth_json_data():
    return {
        "username": "testuser",
        "name": "John Doe",
        "password": "testpassword",
        "native_language": "English",
        "learning_language": "Russian",
        "learning_level": "beginner",
        "email": "testuser@example.com",
    }


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, auth_json_data):
    response = await client.post(
        "/api/v1/auth/register",
        json=auth_json_data
    )
    token = response.json()["access_token"]

    client.headers.update({"Authorization": f"Bearer {token}"})

    return client
