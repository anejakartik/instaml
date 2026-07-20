"""Feature computation correctness — aggregation math + the end-to-end apply_event path."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "sdk"))
sys.path.insert(0, str(_ROOT / "server"))

from instaml.models import Aggregation, Event, FeatureDefinition  # noqa: E402

from compute import _aggregate, apply_event  # noqa: E402
from offline import make_offline_store  # noqa: E402
from online import make_online_store  # noqa: E402


def _event(entity_id: str, event_type: str, amount: float | None = None, minutes_ago: float = 0) -> Event:
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    payload = {} if amount is None else {"amount": amount}
    return Event(entity_id=entity_id, event_type=event_type, timestamp=ts, payload=payload)


# ---- _aggregate (pure) ------------------------------------------------------


def test_aggregate_count() -> None:
    events = [_event("u1", "purchase") for _ in range(4)]
    fd = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.COUNT)
    assert _aggregate(events, fd) == 4.0


def test_aggregate_count_empty() -> None:
    fd = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.COUNT)
    assert _aggregate([], fd) == 0.0


def test_aggregate_sum_and_avg() -> None:
    events = [_event("u1", "purchase", amount=a) for a in (10.0, 20.0, 30.0)]
    fd_sum = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.SUM, field="amount")
    fd_avg = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.AVG, field="amount")
    assert _aggregate(events, fd_sum) == 60.0
    assert _aggregate(events, fd_avg) == 20.0


def test_aggregate_min_max() -> None:
    events = [_event("u1", "purchase", amount=a) for a in (5.0, 99.0, 42.0)]
    fd_min = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.MIN, field="amount")
    fd_max = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.MAX, field="amount")
    assert _aggregate(events, fd_min) == 5.0
    assert _aggregate(events, fd_max) == 99.0


def test_aggregate_last_uses_most_recent_by_timestamp_not_list_order() -> None:
    older = _event("u1", "purchase", amount=1.0, minutes_ago=10)
    newer = _event("u1", "purchase", amount=2.0, minutes_ago=1)
    # Deliberately pass out of chronological order — _aggregate must sort internally.
    fd = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.LAST, field="amount")
    assert _aggregate([older, newer], fd) == 2.0
    assert _aggregate([newer, older], fd) == 2.0


def test_aggregate_sum_missing_field_required_raises() -> None:
    fd = FeatureDefinition(name="n", source_event_type="purchase", aggregation=Aggregation.SUM)
    try:
        _aggregate([_event("u1", "purchase")], fd)
        assert False, "expected ValueError for missing field"
    except ValueError:
        pass


# ---- apply_event (integration: real online + offline stores) ---------------


def _fresh_stores():
    online = make_online_store("memory://")
    online.init()
    db_path = tempfile.mktemp(suffix=".duckdb")
    offline = make_offline_store(db_path)
    offline.init()
    return online, offline


def test_apply_event_only_updates_features_with_matching_event_type() -> None:
    online, offline = _fresh_stores()
    feature_defs = [
        FeatureDefinition(name="purchase_count", source_event_type="purchase", aggregation=Aggregation.COUNT),
        FeatureDefinition(name="view_count", source_event_type="page_view", aggregation=Aggregation.COUNT),
    ]
    event = Event(entity_id="u1", event_type="purchase", payload={})
    updated = apply_event(event, feature_defs, online, offline)

    updated_names = {fv.feature_name for fv in updated}
    assert updated_names == {"purchase_count"}
    assert online.get("u1", "purchase_count") == (1.0, updated[0].updated_at)
    assert online.get("u1", "view_count") is None


def test_apply_event_lifetime_count_accumulates_across_events() -> None:
    online, offline = _fresh_stores()
    feature_defs = [
        FeatureDefinition(name="lifetime_count", source_event_type="purchase", aggregation=Aggregation.COUNT, window="lifetime"),
    ]
    for _ in range(3):
        apply_event(Event(entity_id="u1", event_type="purchase", payload={}), feature_defs, online, offline)

    value, _ = online.get("u1", "lifetime_count")
    assert value == 3.0


def test_apply_event_window_excludes_events_outside_window() -> None:
    online, offline = _fresh_stores()
    feature_defs = [
        FeatureDefinition(name="recent_count", source_event_type="purchase", aggregation=Aggregation.COUNT, window="5m"),
    ]
    # Directly seed an old event straight into the offline store (bypassing
    # apply_event, since apply_event always timestamps "now").
    old_event = _event("u1", "purchase", minutes_ago=30)
    offline.append_event(old_event)

    # A fresh event should only see itself in the 5m window, not the 30m-old one.
    apply_event(Event(entity_id="u1", event_type="purchase", payload={}), feature_defs, online, offline)
    value, _ = online.get("u1", "recent_count")
    assert value == 1.0


def test_apply_event_isolates_entities() -> None:
    online, offline = _fresh_stores()
    feature_defs = [
        FeatureDefinition(name="lifetime_count", source_event_type="purchase", aggregation=Aggregation.COUNT, window="lifetime"),
    ]
    apply_event(Event(entity_id="u1", event_type="purchase", payload={}), feature_defs, online, offline)
    apply_event(Event(entity_id="u2", event_type="purchase", payload={}), feature_defs, online, offline)
    apply_event(Event(entity_id="u2", event_type="purchase", payload={}), feature_defs, online, offline)

    assert online.get("u1", "lifetime_count")[0] == 1.0
    assert online.get("u2", "lifetime_count")[0] == 2.0
