from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from app.core.email import send_reset_email
from app.db.database import get_db
from app.db.crud import create_user, get_user_by_email, get_user_by_username, get_valid_reset_token_user, \
    reset_password_by_token, create_reset_token
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=3, max_length=50)


class UserResponse(BaseModel):
    id: int
    email: str
    username: str


class LoginRequest(BaseModel):
    username: str
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


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = reset_password_by_token(db, request.reset_token, request.new_password)
    if not user:
        raise HTTPException(400, "Invalid or expired token")
    return {"message": "Password reset successfully"}


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    token = create_reset_token(db, request.email)
    if token:
        send_reset_email(request.email, token)

    return {"message": "Если email зарегистрирован, вы получите ссылку для сброса пароля"}


@router.get("/reset-password-form", response_class=HTMLResponse)
def show_reset_form(token: str, db: Session = Depends(get_db)):
    if not get_valid_reset_token_user(db, token):
        return "Неа!"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Сброс пароля</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h2>Сброс пароля</h2>
        <form id="resetForm">
            <input type="hidden" id="token" value="{token}">
            <input type="password" id="new_password" placeholder="Новый пароль" required>
            <button type="submit">Сбросить пароль</button>
        </form>

        <script>
            document.getElementById('resetForm').onsubmit = async (e) => {{
                e.preventDefault();
                await fetch('/auth/reset-password', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        reset_token: document.getElementById('token').value,
                        new_password: document.getElementById('new_password').value
                    }})
                }});
            }};
        </script>
    </body>
    </html>
    """
