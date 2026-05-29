from fastapi import Depends, HTTPException, status, Request, WebSocket
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.db.crud import get_user_by_email
from app.db.database import get_db
from app.db.models import User
from app.core.cache import get_or_set


async def get_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    return token[7:]


async def get_current_user(token: str = Depends(get_token),
                           db: Session = Depends(get_db)) -> User | None | RedirectResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub", '')
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_or_set(
        f"user:email:{email}",
        lambda: get_user_by_email(db, email),
        ttl=30
    )
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_ws(
        websocket: WebSocket,
        db: Session = Depends(get_db)
) -> User | None:
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4001, reason="No token")
        return None

    if token.startswith("Bearer "):
        token = token[7:]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub", '')
        if not email:
            await websocket.close(code=4001, reason="Invalid token")
            return None
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return None

    user = get_user_by_email(db, email)
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return None

    return user


async def get_current_user_optional(
        token: str = Depends(get_token),
        db: Session = Depends(get_db)
) -> User | None:
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = get_user_by_email(db, email)
    return user
