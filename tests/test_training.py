"""Point-in-time training sets: a row's features may only see events at or
before that row's timestamp."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "sdk"))
sys.path.insert(0, str(_ROOT / "server"))

from compute import apply_event, feature_value_as_of  # noqa: E402
from instaml.models import Aggregation, Event, FeatureDefinition, TrainingRow  # noqa: E402
from offline import make_offline_store  # noqa: E402
from online import make_online_store  # noqa: E402
from training import build_training_set  # noqa: E402

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

LIFETIME_COUNT = FeatureDefinition(
    name="lifetime_count", source_event_type="purchase", aggregation=Aggregation.COUNT, window="lifetime"
)
COUNT_5M = FeatureDefinition(name="count_5m", source_event_type="purchase", aggregation=Aggregation.COUNT, window="5m")
LAST_AMOUNT = FeatureDefinition(
    name="last_amount", source_event_type="purchase", aggregation=Aggregation.LAST, field="amount", window="lifetime"
)


def _offline():
    store = make_offline_store(tempfile.mktemp(suffix=".duckdb"))
    store.init()
    return store


def _purchase(entity_id: str, minutes: float, amount: float = 10.0) -> Event:
    return Event(
        entity_id=entity_id,
        event_type="purchase",
        timestamp=T0 + timedelta(minutes=minutes),
        payload={"amount": amount},
    )


def test_events_after_the_row_timestamp_are_not_counted() -> None:
    # The leakage case: 3 purchases, label observed between the 2nd and 3rd.
    offline = _offline()
    for m in (0, 10, 20):
        offline.append_event(_purchase("u1", m))

    [row] = build_training_set(
        [TrainingRow(entity_id="u1", timestamp=T0 + timedelta(minutes=15), label=1)], [LIFETIME_COUNT], offline
    )
    assert row["lifetime_count"] == 2.0  # a naive join against "now" would say 3


def test_window_is_anchored_at_the_row_timestamp_not_now() -> None:
    offline = _offline()
    for m in (0, 3, 30):
        offline.append_event(_purchase("u1", m))

    [row] = build_training_set([TrainingRow(entity_id="u1", timestamp=T0 + timedelta(minutes=4))], [COUNT_5M], offline)
    assert row["count_5m"] == 2.0  # both early events, months before "now"


def test_last_value_is_the_last_one_before_the_row() -> None:
    offline = _offline()
    offline.append_event(_purchase("u1", 0, amount=5.0))
    offline.append_event(_purchase("u1", 10, amount=99.0))

    row_at_5m = TrainingRow(entity_id="u1", timestamp=T0 + timedelta(minutes=5))
    [row] = build_training_set([row_at_5m], [LAST_AMOUNT], offline)
    assert row["last_amount"] == 5.0


def test_event_exactly_at_the_row_timestamp_is_included() -> None:
    offline = _offline()
    offline.append_event(_purchase("u1", 0))
    assert feature_value_as_of("u1", LIFETIME_COUNT, T0, offline) == 1.0


def test_rows_keep_input_order_and_pass_labels_through() -> None:
    offline = _offline()
    offline.append_event(_purchase("u1", 0))
    rows = [
        TrainingRow(entity_id="u2", timestamp=T0 + timedelta(minutes=1), label="no"),
        TrainingRow(entity_id="u1", timestamp=T0 + timedelta(minutes=1), label="yes"),
    ]
    out = build_training_set(rows, [LIFETIME_COUNT], offline)
    assert [(r["entity_id"], r["label"], r["lifetime_count"]) for r in out] == [("u2", "no", 0.0), ("u1", "yes", 1.0)]


def test_feature_name_clashing_with_an_output_column_is_rejected() -> None:
    clash = FeatureDefinition(name="label", source_event_type="purchase", aggregation=Aggregation.COUNT)
    with pytest.raises(ValueError):
        build_training_set([TrainingRow(entity_id="u1", timestamp=T0)], [clash], _offline())


def test_online_value_matches_point_in_time_value_at_now() -> None:
    # Same function on both paths: what gets served is what training sees.
    online, offline = make_online_store("memory://"), _offline()
    online.init()
    for _ in range(3):
        event = Event(entity_id="u1", event_type="purchase", payload={"amount": 1.0})
        apply_event(event, [LIFETIME_COUNT], online, offline)
    served, _ = online.get("u1", "lifetime_count")
    assert served == feature_value_as_of("u1", LIFETIME_COUNT, datetime.now(timezone.utc), offline) == 3.0


def test_leakage_demo_shows_naive_join_inflating_auc() -> None:
    # Keeps examples/leakage_demo.py runnable, and pins the claim it makes.
    sys.path.insert(0, str(_ROOT / "examples"))
    import leakage_demo

    result = leakage_demo.run(seed=7)
    assert result["naive_auc"] > result["pit_auc"] + 0.05
