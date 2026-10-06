"""DuckDB-backed OfflineStore, with a Parquet export/snapshot path.

DuckDB is the store of record (fast native INSERT + indexed lookups for the
window queries `compute.py` runs on every write); `export_parquet()` dumps the
full event log to a Parquet file for portability/analysis in other tools —
that's where "Parquet" in the stack shows up, as a snapshot format rather than
the live write path.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

import duckdb
from instaml.models import Event


class DuckDBOfflineStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._con = duckdb.connect(db_path)

    def init(self) -> None:
        with self._lock:
            self._con.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id VARCHAR PRIMARY KEY,
                    entity_id VARCHAR NOT NULL,
                    event_type VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    payload_json VARCHAR NOT NULL
                )
                """
            )
            self._con.execute(
                "CREATE INDEX IF NOT EXISTS idx_entity_type ON events(entity_id, event_type)"
            )

    def append_event(self, event: Event) -> None:
        with self._lock:
            self._con.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                [
                    str(event.id),
                    event.entity_id,
                    event.event_type,
                    _to_naive_utc(event.timestamp),
                    json.dumps(event.payload),
                ],
            )

    def query_events(
        self,
        *,
        entity_id: str,
        event_type: str,
        since: datetime | None,
        until: datetime | None = None,
    ) -> list[Event]:
        sql = (
            "SELECT id, entity_id, event_type, timestamp, payload_json FROM events "
            "WHERE entity_id = ? AND event_type = ?"
        )
        params: list[object] = [entity_id, event_type]
        if since is not None:
            sql += " AND timestamp >= ?"
            params.append(_to_naive_utc(since))
        if until is not None:
            sql += " AND timestamp <= ?"
            params.append(_to_naive_utc(until))
        with self._lock:
            rows = self._con.execute(sql, params).fetchall()
        return [_row_to_event(r) for r in rows]

    def export_parquet(self, out_path: str) -> None:
        """Snapshot the full event log to a Parquet file — portable format for
        analysis outside instaml (pandas, another DuckDB session, a warehouse
        load, etc.).

        DuckDB's COPY statement doesn't accept a prepared-statement parameter
        for the target path, so this quotes `out_path` itself rather than
        binding it — safe here because callers control this path (it's never
        derived from HTTP request input), unlike append_event/query_events
        which do use bound parameters for actual untrusted data.
        """
        escaped = out_path.replace("'", "''")
        with self._lock:
            self._con.execute(f"COPY events TO '{escaped}' (FORMAT PARQUET)")

    def describe(self) -> str:
        return f"duckdb ({self._db_path}, parquet-exportable)"


def _to_naive_utc(ts: datetime) -> datetime:
    """The `events.timestamp` column is naive UTC. Convert before stripping the
    offset: a bare `.replace(tzinfo=None)` on 12:00+05:30 used to store 12:00
    instead of 06:30, shifting every non-UTC event by its offset. A naive input
    is taken to already be UTC."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc)
    return ts.replace(tzinfo=None)


def _row_to_event(row: tuple) -> Event:
    id_, entity_id, event_type, timestamp, payload_json = row
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return Event(
        id=id_,
        entity_id=entity_id,
        event_type=event_type,
        timestamp=timestamp,
        payload=json.loads(payload_json),
    )
