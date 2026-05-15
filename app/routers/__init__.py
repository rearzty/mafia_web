from fastapi import APIRouter
from app.routers import auth, profile

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(profile.router, prefix="/profile", tags=["profile"])
