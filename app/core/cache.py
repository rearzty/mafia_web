from app.core.redis_client import redis_client
from app.schemas.user import UserResponse


async def get_or_set(cache_key: str, fetcher, ttl: int = 10):
    cached = await redis_client.get(cache_key)
    if cached is not None:
        return UserResponse.model_validate_json(cached)
    data = await fetcher()
    json_data = UserResponse.model_validate(data).model_dump_json()
    await redis_client.setex(cache_key, ttl, json_data)
    return data


async def invalidate(cache_key: str):
    await redis_client.delete(cache_key)


async def invalidate_pattern(pattern: str):
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
