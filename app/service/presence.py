import time

from app.db.cache_redis import redis_client
from app.config import settings


async def mark_online(user_id: int) -> None:
    await redis_client.set(f"online:{user_id}", "1", ex=settings.ONLINE_TTL)
    await redis_client.set(f"last_seen:{user_id}", int(time.time()), ex=settings.LAST_SEEN_TTL)


async def mark_offline(user_id: int) -> None:
    await redis_client.delete(f"online:{user_id}")
    await redis_client.set(f"last_seen:{user_id}", int(time.time()), ex=settings.LAST_SEEN_TTL)


async def get_status(user_id: int) -> dict:
    if await redis_client.exists(f"online:{user_id}"):
        return {"online": True}

    last_seen = await redis_client.get(f"last_seen:{user_id}")

    if last_seen is None:
        return {"online": False, "last_seen": None}

    return {"online": False, "last_seen": int(last_seen)}
