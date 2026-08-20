import pytest


@pytest.mark.asyncio
async def test_register_creates_user(client):
    response = await client.post("/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "password123",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@test.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client):
    payload = {"email": "dup@test.com", "username": "user1", "password": "password123"}
    await client.post("/auth/register", json=payload)

    response = await client.post("/auth/register", json={**payload, "username": "user2"})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_same_response_for_existing_and_nonexistent_email(client):
    await client.post("/auth/register", json={
        "email": "real@test.com", "username": "real", "password": "password123",
    })

    resp_real = await client.post("/auth/forgot-password", json={"email": "real@test.com"})
    resp_fake = await client.post("/auth/forgot-password", json={"email": "ghost@test.com"})

    assert resp_real.json() == resp_fake.json()
    assert resp_real.status_code == resp_fake.status_code
