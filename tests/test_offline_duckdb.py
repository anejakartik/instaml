"""DuckDBOfflineStore: append + window-filtered query + Parquet export."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "sdk"))
sys.path.insert(0, str(_ROOT / "server"))

from instaml.models import Event  # noqa: E402
from offline._parquet import DuckDBOfflineStore  # noqa: E402


def _store() -> DuckDBOfflineStore:
    store = DuckDBOfflineStore(tempfile.mktemp(suffix=".duckdb"))
    store.init()
    return store


def test_append_then_query_round_trips() -> None:
    store = _store()
    event = Event(entity_id="u1", event_type="purchase", payload={"amount": 19.99})
    store.append_event(event)

    rows = store.query_events(entity_id="u1", event_type="purchase", since=None)
    assert len(rows) == 1
    assert rows[0].entity_id == "u1"
    assert rows[0].payload == {"amount": 19.99}


def test_query_filters_by_entity_and_event_type() -> None:
    store = _store()
    store.append_event(Event(entity_id="u1", event_type="purchase", payload={}))
    store.append_event(Event(entity_id="u2", event_type="purchase", payload={}))
    store.append_event(Event(entity_id="u1", event_type="page_view", payload={}))

    rows = store.query_events(entity_id="u1", event_type="purchase", since=None)
    assert len(rows) == 1
    assert rows[0].entity_id == "u1"
    assert rows[0].event_type == "purchase"


def test_query_since_excludes_older_events() -> None:
    store = _store()
    now = datetime.now(timezone.utc)
    old = Event(entity_id="u1", event_type="purchase", timestamp=now - timedelta(hours=2), payload={})
    recent = Event(entity_id="u1", event_type="purchase", timestamp=now - timedelta(minutes=1), payload={})
    store.append_event(old)
    store.append_event(recent)

    rows = store.query_events(entity_id="u1", event_type="purchase", since=now - timedelta(minutes=10))
    assert len(rows) == 1
    assert rows[0].id == recent.id


def test_export_parquet_writes_a_readable_file() -> None:
    import duckdb

    store = _store()
    store.append_event(Event(entity_id="u1", event_type="purchase", payload={"amount": 5.0}))
    out_path = tempfile.mktemp(suffix=".parquet")
    store.export_parquet(out_path)

    con = duckdb.connect()
    count = con.execute(f"SELECT count(*) FROM read_parquet('{out_path}')").fetchone()[0]
    assert count == 1
