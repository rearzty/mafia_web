from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.crud import create_user, get_user_by_email, get_user_by_username, get_valid_reset_token_user, \
    reset_password_by_token, create_reset_token
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.routers.pages import templates
from app.schemas.user import UserResponse, RegisterRequest, TokenResponse, ResetPasswordRequest, ForgotPasswordRequest
from app.core.celery.tasks import send_reset_email_task

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_data: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    if await get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Такой email уже зарегистрирован")

    if await get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Такое имя пользователя уже занято")

    hashed = hash_password(user_data.password)
    user = await create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed
    )
    return UserResponse(id=user.id, email=user.email, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("access_token")
    return response


@router.get("/forgot-password-page", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    token = await create_reset_token(db, request.email)
    if token:
        send_reset_email_task.delay(request.email, token)
    return {"message": "Если email зарегистрирован, вы получите ссылку"}


@router.get("/reset-password-form", response_class=HTMLResponse)
async def show_reset_form(request: Request, token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    if not await get_valid_reset_token_user(db, token):
        return HTMLResponse("Ссылка недействительна или истекла")
    return templates.TemplateResponse(request, name="reset_password_form.html", context={"token": token})


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await reset_password_by_token(db, request.reset_token, request.new_password)
    if not user:
        raise HTTPException(400, "Неверный токен")
    return {"message": "Пароль успешно установлен"}
