"""Redis connection management."""

import json
from typing import Any, Optional

import aioredis
from aioredis import Redis

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    try:
        redis = await get_redis()
        val = await redis.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Cache get failed: {e}", key=key)
    return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache with optional TTL."""
    try:
        redis = await get_redis()
        ttl = ttl or settings.redis_cache_ttl
        await redis.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Cache set failed: {e}", key=key)
        return False
