from fastapi import APIRouter
from app.routers import auth, game, pages

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(game.router, prefix="/game", tags=["game"])
router.include_router(pages.router, tags=["pages"])
