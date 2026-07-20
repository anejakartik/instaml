"""Offline store abstraction — the durable event log every feature is computed from.

Single implementation for the MVP: DuckDB-backed (see `_parquet.py`). DuckDB
gives us fast native appends *and* first-class Parquet export/query, so the
"Parquet" part of the stated stack is the store's portable snapshot format
(`export_parquet()`) rather than the live write path — real per-row Parquet
appends aren't a thing Parquet supports, and faking it with constant file
rewrites would be slower and more fragile than just using DuckDB natively.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from instaml.models import Event


class OfflineStore(Protocol):
    """Append-only event log. Implementations MUST be thread-safe."""

    def init(self) -> None: ...

    def append_event(self, event: Event) -> None: ...

    def query_events(
        self,
        *,
        entity_id: str,
        event_type: str,
        since: datetime | None,
    ) -> list[Event]:
        """All matching events, since=None means unbounded (lifetime window)."""
        ...

    def describe(self) -> str: ...


def make_offline_store(db_path: str) -> OfflineStore:
    from ._parquet import DuckDBOfflineStore

    return DuckDBOfflineStore(db_path)
