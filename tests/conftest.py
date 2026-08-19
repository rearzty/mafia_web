import os
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.game.storage import mafia_games, mafia_players

load_dotenv(".env.test")
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def db_setup():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db_setup):
    async with TestSessionLocal() as session:
        yield session

        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())

        await session.commit()


@pytest_asyncio.fixture(autouse=True)
def clear_game_storage():
    mafia_games.clear()
    mafia_players.clear()
    yield
    mafia_games.clear()
    mafia_players.clear()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client):
    payload = {"email": "player@test.com", "username": "player1", "password": "password123"}
    await client.post("/auth/register", json=payload)

    login_resp = await client.post("/auth/login", data={
        "username": payload["email"],
        "password": payload["password"],
    })
    assert login_resp.status_code == 200
    return client, payload
