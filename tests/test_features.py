"""Feature-def YAML loading + window parsing."""

from __future__ import annotations

import sys
import tempfile
from datetime import timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "sdk"))

from instaml.features import load_feature_defs  # noqa: E402
from instaml.models import Aggregation, FeatureDefinition  # noqa: E402


def test_window_delta_parses_minutes_hours_days_seconds() -> None:
    assert FeatureDefinition(
        name="a", source_event_type="e", aggregation=Aggregation.COUNT, window="5m"
    ).window_delta() == timedelta(minutes=5)
    assert FeatureDefinition(
        name="a", source_event_type="e", aggregation=Aggregation.COUNT, window="2h"
    ).window_delta() == timedelta(hours=2)
    assert FeatureDefinition(
        name="a", source_event_type="e", aggregation=Aggregation.COUNT, window="7d"
    ).window_delta() == timedelta(days=7)
    assert FeatureDefinition(
        name="a", source_event_type="e", aggregation=Aggregation.COUNT, window="30s"
    ).window_delta() == timedelta(seconds=30)


def test_window_delta_lifetime_is_unbounded() -> None:
    fd = FeatureDefinition(name="a", source_event_type="e", aggregation=Aggregation.COUNT, window="lifetime")
    assert fd.window_delta() is None


def test_window_delta_rejects_unknown_unit() -> None:
    fd = FeatureDefinition(name="a", source_event_type="e", aggregation=Aggregation.COUNT, window="5x")
    try:
        fd.window_delta()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_load_feature_defs_from_yaml() -> None:
    yaml_text = """
features:
  - name: purchases_last_5m
    source_event_type: purchase
    aggregation: count
    window: 5m
  - name: avg_cart_value_1h
    source_event_type: purchase
    aggregation: avg
    field: amount
    window: 1h
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_text)
        path = f.name

    defs = load_feature_defs(path)
    assert len(defs) == 2
    assert defs[0].name == "purchases_last_5m"
    assert defs[0].aggregation == Aggregation.COUNT
    assert defs[1].field == "amount"


def test_demo_yaml_loads_cleanly() -> None:
    """The actual demo.yaml shipped with the repo must parse without error."""
    defs = load_feature_defs(_ROOT / "features" / "demo.yaml")
    assert len(defs) >= 4
    names = {fd.name for fd in defs}
    assert "purchases_last_5m" in names
    assert "lifetime_total_spend" in names
