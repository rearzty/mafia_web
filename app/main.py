from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import router
from app.middleware import setup_middlewares
from app.core.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.init()
    yield


app = FastAPI(title="Mafia Game", lifespan=lifespan)

app.include_router(router)
setup_middlewares(app)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
