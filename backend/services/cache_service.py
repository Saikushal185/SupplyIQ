"""Redis cache helpers for SupplyIQ."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from redis import Redis

from backend.settings import get_settings


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

    def __init__(self) -> None:
        settings = get_settings()
        self._ttl_seconds = settings.cache_ttl_seconds
        self._client = Redis.from_url(settings.redis_url, decode_responses=True)

    def build_key(self, namespace: str, payload: dict[str, object]) -> str:
        """Builds a stable cache key from a namespace and parameter payload."""

        digest = hashlib.md5(
            json.dumps(payload, sort_keys=True, default=_serialize_value).encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        return f"supplyiq:{namespace}:{digest}"

    def get_json(self, key: str) -> dict[str, object] | list[object] | None:
        """Returns cached JSON data if it exists."""

        raw_value = self._client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)

    def set_json(self, key: str, value: object) -> None:
        """Stores JSON-serializable data in Redis with the default TTL."""

        serialized = json.dumps(value, default=_serialize_value)
        self._client.setex(key, self._ttl_seconds, serialized)
