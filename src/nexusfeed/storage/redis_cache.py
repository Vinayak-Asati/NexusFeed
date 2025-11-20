import os
import json
from typing import Optional

from redis.asyncio import Redis


_client: Optional[Redis] = None


def _get_url() -> str:
    url = os.getenv("REDIS_URL")
    if url:
        return url
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "0")
    return f"redis://{host}:{port}/{db}"


async def get_client() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(_get_url(), encoding="utf-8", decode_responses=True)
    return _client


async def set_snapshot(instrument: str, snapshot: dict) -> None:
    client = await get_client()
    key = f"book:{instrument}"
    await client.set(key, json.dumps(snapshot))


async def get_snapshot(instrument: str) -> Optional[dict]:
    try:
        client = await get_client()
        key = f"book:{instrument}"
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception:
        return None