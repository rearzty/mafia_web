from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_client import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limits: dict):
        super().__init__(app)
        self.limits = limits

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        path = request.url.path

        for rule_path, config in self.limits.items():
            if path.startswith(rule_path.rstrip('*')):
                key = f"rate:{client_ip}:{path}"
                limit = config["limit"]
                period = config["period"]

                count = await redis_client.incr(key)
                if count == 1:
                    await redis_client.expire(key, period)

                if count > limit:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": f"Слишком много запросов. Лимит: {limit} за {period} секунд."}
                    )

        return await call_next(request)
