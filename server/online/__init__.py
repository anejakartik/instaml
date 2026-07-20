"""Online store abstraction — fast point lookups of the latest feature value.

Two implementations:
- In-memory dict (default) — zero-config, single-process, fine for local dev
  and the CI test suite.
- Redis (via INSTAML_ONLINE_URL=redis://...) — used for the hosted demo, since
  a real online store needs to survive across the Fly.io machine's request
  lifecycle and be shareable if the app ever scales past one instance.

Feature *values* are always recomputed from the OfflineStore's raw events on
every write (see server/compute.py) — the online store's only job is storing
the latest computed point value for O(1) reads, not doing any aggregation
itself. Keeping it this dumb is what makes swapping in Redis a one-file change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class OnlineStore(Protocol):
    """Point-value store. Implementations MUST be thread-safe."""

    def init(self) -> None: ...

    def set(self, entity_id: str, feature_name: str, value: float, updated_at: datetime) -> None: ...

    def get(self, entity_id: str, feature_name: str) -> tuple[float, datetime] | None: ...

    def entity_count(self, feature_name: str) -> int:
        """How many distinct entities currently have a value for this feature —
        used by the /catalog endpoint so the dashboard shows the catalog is
        live, not just declared."""
        ...

    def describe(self) -> str: ...


def make_online_store(url: str) -> OnlineStore:
    """Factory — branches on URL scheme."""
    if url.startswith("redis://") or url.startswith("rediss://"):
        from ._redis import RedisOnlineStore

        return RedisOnlineStore(url)
    from ._memory import InMemoryOnlineStore

    return InMemoryOnlineStore()
