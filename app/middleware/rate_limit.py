from fastapi import Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
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
            if path.startswith(rule_path) and not path.endswith("/status"):
                key = f"rate:{client_ip}:{rule_path}"
                limit = config["limit"]
                period = config["period"]

                client = redis_client.get_client()
                if client:
                    try:
                        async with client.pipeline() as pipe:
                            pipe.incr(key)
                            pipe.expire(key, period, nx=True)
                            count, _ = await pipe.execute()
                    except RedisError:
                        break

                    if count > limit:
                        return JSONResponse(
                            status_code=429,
                            content={"detail": "Слишком много запросов"}
                        )
                break

        return await call_next(request)
