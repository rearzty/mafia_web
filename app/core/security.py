import hashlib
import bcrypt
from datetime import datetime, timedelta
from app.core.config import settings
from jose import jwt


def hash_password(password: str) -> str:
    sha256_hash = hashlib.sha256(password.encode()).digest()
    return bcrypt.hashpw(sha256_hash, bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    sha256_hash = hashlib.sha256(plain_password.encode()).digest()
    return bcrypt.checkpw(sha256_hash, hashed_password.encode())


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
