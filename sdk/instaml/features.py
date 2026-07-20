"""Load declarative feature definitions from a YAML file.

Feature-defs file shape:

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
      - name: lifetime_purchase_count
        source_event_type: purchase
        aggregation: count
        window: lifetime
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import FeatureDefinition


def load_feature_defs(path: str | Path) -> list[FeatureDefinition]:
    """Parse a YAML feature-defs file into a list of FeatureDefinition.

    Raises FileNotFoundError / pydantic.ValidationError on bad input — feature
    definitions are config, not runtime data, so fail loud at startup rather
    than silently skip a malformed feature.
    """
    text = Path(path).read_text()
    raw = yaml.safe_load(text) or {}
    entries = raw.get("features", [])
    return [FeatureDefinition(**entry) for entry in entries]
