"""In-process dict-backed OnlineStore. Default for local dev — zero config."""

from __future__ import annotations

import threading
from datetime import datetime


class InMemoryOnlineStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple[str, str], tuple[float, datetime]] = {}

    def init(self) -> None:
        pass

    def set(self, entity_id: str, feature_name: str, value: float, updated_at: datetime) -> None:
        with self._lock:
            self._values[(entity_id, feature_name)] = (value, updated_at)

    def get(self, entity_id: str, feature_name: str) -> tuple[float, datetime] | None:
        with self._lock:
            return self._values.get((entity_id, feature_name))

    def entity_count(self, feature_name: str) -> int:
        with self._lock:
            return sum(1 for (_, fname) in self._values if fname == feature_name)

    def describe(self) -> str:
        return "memory (in-process, not shared across instances)"
