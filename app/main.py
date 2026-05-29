from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import router
from app.middleware import setup_middlewares

app = FastAPI(title="Mafia Game")

app.include_router(router)
setup_middlewares(app)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
