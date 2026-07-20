"""InMemoryOnlineStore round-trip + isolation."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "server"))

from online._memory import InMemoryOnlineStore  # noqa: E402


def test_get_missing_returns_none() -> None:
    store = InMemoryOnlineStore()
    store.init()
    assert store.get("u1", "f1") is None


def test_set_then_get_round_trips() -> None:
    store = InMemoryOnlineStore()
    store.init()
    now = datetime.now(timezone.utc)
    store.set("u1", "f1", 42.0, now)
    value, updated_at = store.get("u1", "f1")
    assert value == 42.0
    assert updated_at == now


def test_set_overwrites_previous_value() -> None:
    store = InMemoryOnlineStore()
    store.init()
    now = datetime.now(timezone.utc)
    store.set("u1", "f1", 1.0, now)
    store.set("u1", "f1", 2.0, now)
    value, _ = store.get("u1", "f1")
    assert value == 2.0


def test_isolates_by_entity_and_feature_name() -> None:
    store = InMemoryOnlineStore()
    store.init()
    now = datetime.now(timezone.utc)
    store.set("u1", "f1", 1.0, now)
    store.set("u2", "f1", 2.0, now)
    store.set("u1", "f2", 3.0, now)
    assert store.get("u1", "f1")[0] == 1.0
    assert store.get("u2", "f1")[0] == 2.0
    assert store.get("u1", "f2")[0] == 3.0


def test_entity_count() -> None:
    store = InMemoryOnlineStore()
    store.init()
    now = datetime.now(timezone.utc)
    store.set("u1", "f1", 1.0, now)
    store.set("u2", "f1", 2.0, now)
    store.set("u3", "f2", 3.0, now)
    assert store.entity_count("f1") == 2
    assert store.entity_count("f2") == 1
    assert store.entity_count("unknown") == 0
