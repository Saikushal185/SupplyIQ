"""Async Redis cache helpers for SupplyIQ."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.settings import get_settings

logger = logging.getLogger(__name__)


def _serialize_value(value: object) -> object:
    """Converts non-JSON-native values into cache-safe representations."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


class CacheService:
    """Provides simple JSON caching around Redis."""

    def __init__(self, client: Redis | None = None, ttl_seconds: int | None = None) -> None:
        """Builds the cache service with optional injected client dependencies."""

        settings = get_settings()
        self._ttl_seconds = ttl_seconds or settings.cache_ttl_seconds
        self._client = client or Redis.from_url(settings.redis_url, decode_responses=True)

    def build_key(self, namespace: str, payload: dict[str, object]) -> str:
        """Builds a stable cache key from a namespace and parameter payload."""

        digest = hashlib.md5(
            json.dumps(payload, sort_keys=True, default=_serialize_value).encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        return f"supplyiq:{namespace}:{digest}"

    async def get_json(self, key: str) -> dict[str, object] | list[object] | None:
        """Returns cached JSON data if it exists."""

        try:
            raw_value = await self._client.get(key)
        except (RedisError, OSError, RuntimeError) as exc:
            logger.warning("Redis get failed for %s: %s", key, exc)
            return None
        if raw_value is None:
            return None
        return json.loads(raw_value)

    async def set_json(self, key: str, value: object) -> None:
        """Stores JSON-serializable data in Redis with the default TTL."""

        serialized = json.dumps(value, default=_serialize_value)
        try:
            await self._client.setex(key, self._ttl_seconds, serialized)
        except (RedisError, OSError, RuntimeError) as exc:
            logger.warning("Redis set failed for %s: %s", key, exc)

    async def ping(self) -> bool:
        """Checks whether the backing Redis client is reachable."""

        try:
            return bool(await self._client.ping())
        except (RedisError, OSError, RuntimeError) as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False

    async def delete_key(self, key: str) -> bool:
        """Deletes a single cache key. Returns True if the key existed."""

        try:
            deleted = await self._client.delete(key)
            return bool(deleted)
        except (RedisError, OSError, RuntimeError) as exc:
            logger.warning("Redis delete failed for %s: %s", key, exc)
            return False

    async def clear_namespace(self, namespace: str) -> int:
        """Deletes all keys matching a namespace prefix. Returns count deleted."""

        pattern = f"supplyiq:{namespace}:*"
        try:
            keys = [key async for key in self._client.scan_iter(match=pattern)]
            if not keys:
                return 0
            return int(await self._client.delete(*keys))
        except (RedisError, OSError, RuntimeError) as exc:
            logger.warning("Redis clear_namespace failed for %s: %s", namespace, exc)
            return 0

    async def close(self) -> None:
        """Closes the underlying Redis client."""

        try:
            await self._client.aclose()
        except (RedisError, OSError, RuntimeError):
            logger.warning("Redis close failed.", exc_info=True)
