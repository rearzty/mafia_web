from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.db.crud import create_user, get_user_by_email, get_user_by_username
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str


class LoginRequest(BaseModel):
    username: str  # будем использовать email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/register", response_model=UserResponse)
def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    # Проверяем, не занят ли email
    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Проверяем, не занят ли username
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Создаем пользователя
    hashed = hash_password(user_data.password)
    user = create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed
    )
    access_token = create_access_token(data={"sub": user.email})
    return UserResponse(id=user.id, email=user.email, username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
