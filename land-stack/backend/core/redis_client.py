"""
core/redis_client.py — Redis connection factory and FastAPI dependency.

Environment variable:
  REDIS_URL  — Redis connection URL (default: redis://localhost:6379)
"""

import os
from dotenv import load_dotenv
load_dotenv()

import redis.asyncio as aioredis

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")


async def get_redis() -> aioredis.Redis:
    """
    Return a Redis client connected to REDIS_URL.

    Use as a FastAPI dependency::

        redis: aioredis.Redis = Depends(get_redis)

    The caller is responsible for closing the client when it is no longer needed.
    For short-lived request handlers the connection is returned to the pool
    automatically via the underlying connection pool lifecycle.
    """
    return aioredis.from_url(REDIS_URL, decode_responses=True)
