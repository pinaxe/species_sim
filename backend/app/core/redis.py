"""Redis connection management."""

import json
from typing import Any, Optional

try:
    from redis.asyncio import Redis
except ImportError:
    from aioredis import Redis

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[Redis] = None


async def get_redis() -> Optional[Redis]:
    """Get or create Redis client. Returns None if Redis unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            if Redis.__module__.startswith("redis.asyncio"):
                _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
            else:
                import aioredis
                _redis_client = await aioredis.from_url(
                    settings.redis_url,
                    encoding="utf8",
                    decode_responses=True,
                )
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            _redis_client = None
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.close()
        except Exception as e:
            logger.warning(f"Error closing Redis: {e}")
        _redis_client = None


async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    try:
        redis = await get_redis()
        if redis is None:
            return None
        val = await redis.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Cache get failed: {e}")
    return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache with optional TTL."""
    try:
        redis = await get_redis()
        if redis is None:
            return False
        ttl = ttl or settings.redis_cache_ttl
        await redis.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Cache set failed: {e}")
        return False
