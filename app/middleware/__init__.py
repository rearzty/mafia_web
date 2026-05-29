from fastapi import FastAPI
from app.middleware.rate_limit import RateLimitMiddleware

RATE_LIMITS = {
    "/auth/login": {"limit": 5, "period": 60},
    "/auth/register": {"limit": 3, "period": 60},
    "/auth/forgot-password": {"limit": 2, "period": 60},
    "/game/": {"limit": 30, "period": 60},
    "/profile/": {"limit": 100, "period": 60},
}


def setup_middlewares(app: FastAPI):
    app.add_middleware(RateLimitMiddleware, limits=RATE_LIMITS)
