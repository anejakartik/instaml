"""How much does a naive feature join leak? A self-contained, synthetic answer.

Simulates 500 users over 60 days. Each user has a hidden purchase rate. The
label for each user is "purchased in the 14 days after the snapshot date
(day 30)". The feature is `lifetime_purchase_count`.

Two ways to build the training table:
  naive         join labels against the feature's value *today* (day 60), the
                way you would if you just read the online store
  point-in-time `build_training_set`: the value as of the snapshot date

The naive table counts the very purchases that define the label, so the
feature looks far more predictive offline than it can ever be in production.

No server, Redis or API keys needed:
    PYTHONPATH=./sdk:./server python examples/leakage_demo.py
"""

from __future__ import annotations

import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "sdk"))
sys.path.insert(0, str(_ROOT / "server"))

from compute import feature_value_as_of  # noqa: E402
from instaml.models import Aggregation, Event, FeatureDefinition, TrainingRow  # noqa: E402
from offline import make_offline_store  # noqa: E402
from training import build_training_set  # noqa: E402

START = datetime(2026, 7, 1, tzinfo=timezone.utc)
SNAPSHOT = START + timedelta(days=30)
LABEL_HORIZON = timedelta(days=14)
TODAY = START + timedelta(days=60)
N_USERS = 500

FEATURE = FeatureDefinition(
    name="lifetime_purchase_count", source_event_type="purchase", aggregation=Aggregation.COUNT, window="lifetime"
)


def auc(scores: list[float], labels: list[int]) -> float:
    """Probability a random positive outranks a random negative (ties = 0.5)."""
    pos = [s for s, y in zip(scores, labels, strict=True) if y]
    neg = [s for s, y in zip(scores, labels, strict=True) if not y]
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def run(seed: int = 7) -> dict[str, float]:
    rng = random.Random(seed)
    offline = make_offline_store(tempfile.mktemp(suffix=".duckdb"))
    offline.init()

    labels: dict[str, int] = {}
    for i in range(N_USERS):
        user = f"user_{i}"
        rate_per_day = rng.choice([0.0, 0.02, 0.05, 0.1, 0.2])
        bought_in_horizon = False
        for day in range(60):
            if rng.random() < rate_per_day:
                ts = START + timedelta(days=day, hours=rng.uniform(0, 24))
                offline.append_event(Event(entity_id=user, event_type="purchase", timestamp=ts))
                if SNAPSHOT < ts <= SNAPSHOT + LABEL_HORIZON:
                    bought_in_horizon = True
        labels[user] = int(bought_in_horizon)

    users = sorted(labels)
    y = [labels[u] for u in users]

    naive = [feature_value_as_of(u, FEATURE, TODAY, offline) for u in users]
    rows = [TrainingRow(entity_id=u, timestamp=SNAPSHOT, label=labels[u]) for u in users]
    pit = [r[FEATURE.name] for r in build_training_set(rows, [FEATURE], offline)]

    return {
        "positives": sum(y),
        "rows_changed": sum(a != b for a, b in zip(naive, pit, strict=True)),
        "naive_auc": auc(naive, y),
        "pit_auc": auc(pit, y),
    }


def main() -> None:
    r = run()
    print(f"{N_USERS} users, {r['positives']} positive labels (bought within 14 days of the snapshot)")
    print(f"rows whose feature value differs between the two joins: {r['rows_changed']}/{N_USERS}")
    print(f"AUC of {FEATURE.name} alone, naive join:         {r['naive_auc']:.3f}")
    print(f"AUC of {FEATURE.name} alone, point-in-time join: {r['pit_auc']:.3f}")


if __name__ == "__main__":
    main()
