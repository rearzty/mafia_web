from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_current_user

router = APIRouter()


class UserResponse(BaseModel):
    id: int
    email: str
    username: str


@router.get("/me", response_model=UserResponse)
def get_profile(current_user=Depends(get_current_user)):
    return current_user
