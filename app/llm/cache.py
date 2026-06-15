import hashlib
import json
import logging
import os
from typing import Any, Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


def generate_cache_key(model: str, prompt_version: str, user_message: str) -> str:
    """Generate SHA256 cache key from model, prompt version, and user message."""
    combined = f"{model}:{prompt_version}:{user_message}".encode()
    return hashlib.sha256(combined).hexdigest()


async def get_redis_client() -> Optional[Any]:
    """Get async Redis client from environment."""
    if redis is None:
        logger.warning("redis-py not installed; caching disabled")
        return None

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        client = await redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        return client
    except Exception as e:
        logger.warning(f"Failed to connect to Redis at {redis_url}: {e}; caching disabled")
        return None


async def get_cached_response(
    model: str, prompt_version: str, user_message: str
) -> Optional[dict]:
    """Retrieve cached response from Redis."""
    client = await get_redis_client()
    if client is None:
        return None

    try:
        key = generate_cache_key(model, prompt_version, user_message)
        cached_json = await client.get(key)
        if cached_json:
            logger.debug(f"Cache hit for key {key[:16]}...")
            return json.loads(cached_json)
        return None
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")
        return None
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def set_cached_response(
    model: str, prompt_version: str, user_message: str, response: dict, ttl_seconds: int = 86400
) -> None:
    """Store response in Redis cache with TTL."""
    client = await get_redis_client()
    if client is None:
        return

    try:
        key = generate_cache_key(model, prompt_version, user_message)
        await client.setex(key, ttl_seconds, json.dumps(response))
        logger.debug(f"Cached response for key {key[:16]}... (TTL: {ttl_seconds}s)")
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def invalidate_cache(model: str, prompt_version: str, user_message: str) -> None:
    """Remove a specific entry from cache."""
    client = await get_redis_client()
    if client is None:
        return

    try:
        key = generate_cache_key(model, prompt_version, user_message)
        await client.delete(key)
        logger.debug(f"Invalidated cache for key {key[:16]}...")
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")
    finally:
        try:
            await client.close()
        except Exception:
            pass
