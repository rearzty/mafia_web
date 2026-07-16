import secrets
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import hash_password
from app.db.models import User


async def create_user(db: AsyncSession, email: str, username: str, hashed_password: str) -> User:
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_reset_token(db: AsyncSession, email: str) -> str | None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(hours=1)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None
    user.reset_token = token
    user.reset_token_expires = expires
    await db.commit()
    return token


async def get_valid_reset_token_user(db: AsyncSession, token: str) -> User | None:
    result = await db.execute(
        select(User).where(
            User.reset_token == token,
            User.reset_token_expires > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def reset_password_by_token(db: AsyncSession, token: str, new_password: str) -> User | None:
    user = await get_valid_reset_token_user(db, token)
    if not user:
        return None
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()
