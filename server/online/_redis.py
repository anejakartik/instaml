"""Redis-backed OnlineStore — used for the hosted demo (INSTAML_ONLINE_URL=redis://...).

Each feature value is stored as a small hash (`value`, `updated_at`) under
`instaml:v:{feature_name}:{entity_id}`, plus the entity_id is added to a set
at `instaml:entities:{feature_name}` so entity_count() is O(1) via SCARD
instead of an expensive KEYS scan.
"""

from __future__ import annotations

from datetime import datetime, timezone

import redis


class RedisOnlineStore:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client = redis.from_url(url, decode_responses=True)

    def init(self) -> None:
        self._client.ping()

    def set(self, entity_id: str, feature_name: str, value: float, updated_at: datetime) -> None:
        key = self._value_key(feature_name, entity_id)
        self._client.hset(key, mapping={"value": value, "updated_at": updated_at.isoformat()})
        self._client.sadd(self._entities_key(feature_name), entity_id)

    def get(self, entity_id: str, feature_name: str) -> tuple[float, datetime] | None:
        row = self._client.hgetall(self._value_key(feature_name, entity_id))
        if not row:
            return None
        updated_at = datetime.fromisoformat(row["updated_at"])
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return float(row["value"]), updated_at

    def entity_count(self, feature_name: str) -> int:
        return self._client.scard(self._entities_key(feature_name))

    def describe(self) -> str:
        return f"redis ({self._url.split('@')[-1]})"

    @staticmethod
    def _value_key(feature_name: str, entity_id: str) -> str:
        return f"instaml:v:{feature_name}:{entity_id}"

    @staticmethod
    def _entities_key(feature_name: str) -> str:
        return f"instaml:entities:{feature_name}"
