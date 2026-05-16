import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.security import hash_password
from app.db.models import User


def create_user(db: Session, email: str, username: str, hashed_password: str) -> User:
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_reset_token(db: Session, email: str) -> str | None:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        return None
    user.reset_token = token
    user.reset_token_expires = expires
    db.commit()
    return token


def get_valid_reset_token_user(db: Session, token: str) -> User | None:
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires > datetime.utcnow()
    ).first()
    return user


def reset_password_by_token(db: Session, token: str, new_password: str) -> User | None:
    user = get_valid_reset_token_user(db, token)
    if not user:
        return None
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()
