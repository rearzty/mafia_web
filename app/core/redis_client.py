import asyncio

import redis.asyncio as redis
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self.redis_client = None
        self._reconnecting = False
        self._reconnect_task = None

    async def init(self):
        await self._try_connect()

    async def _try_connect(self):
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await client.ping()
            self.redis_client = client
        except (redis.ConnectionError, redis.TimeoutError, redis.RedisError):
            self.redis_client = None

    def get_client(self):
        if self.redis_client is None and not self._reconnecting:
            self._reconnecting = True
            self._reconnect_task = asyncio.create_task(self.reconnect())
        return self.redis_client

    async def reconnect(self):
        await self._try_connect()
        self._reconnecting = False
        self._reconnect_task = None


redis_client = RedisClient()
