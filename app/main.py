from fastapi import FastAPI
from app.routers import router

app = FastAPI(title="Mafia Game")

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Mafia Game API"}
