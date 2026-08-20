import os
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.game.storage import mafia_games, mafia_players
from unittest.mock import patch

load_dotenv(".env.test")
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest_asyncio.fixture(autouse=True)
def clear_game_storage():
    mafia_games.clear()
    mafia_players.clear()
    yield
    mafia_games.clear()
    mafia_players.clear()


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(TEST_DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


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


@pytest_asyncio.fixture(autouse=True)
def mock_celery_tasks():
    with patch("app.routers.auth.send_reset_email_task.delay"):
        yield
