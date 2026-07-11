from app.core.redis_client import redis_client
from app.schemas.user import UserResponse
from redis.asyncio.client import Redis


def client_connected(func):
    async def wrapper(*args, **kwargs):
        client = redis_client.get_client()
        if client:
            return await func(client, *args, **kwargs)
        return await func(None, *args, **kwargs)

    return wrapper


@client_connected
async def get_or_set(client: Redis | None, cache_key: str, fetcher, ttl: int = 10):
    if client is None:
        data = await fetcher()
        return UserResponse.model_validate(data) if data is not None else None
    cached = await client.get(cache_key)
    if cached is not None:
        return UserResponse.model_validate_json(cached)
    data = await fetcher()
    if data is None:
        return None
    response = UserResponse.model_validate(data)
    await client.setex(cache_key, ttl, response.model_dump_json())
    return response


@client_connected
async def invalidate(client, cache_key: str):
    if client is None:
        return
    await client.delete(cache_key)


@client_connected
async def invalidate_pattern(client, pattern: str):
    if client is None:
        return
    keys = await client.keys(pattern)
    if keys:
        await client.delete(*keys)
