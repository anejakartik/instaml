"""Point-in-time-correct training datasets.

A training row is (entity_id, timestamp, label): "at this moment, this user
did / didn't churn". Its features must be the values the model *would have
seen* at that moment. Joining labels against today's online values instead
leaks the future into training: a purchase made after the label's timestamp
inflates `lifetime_purchase_count` for that row, the model learns from a
signal it will never have at serving time, and offline metrics look better
than production ever will.

So every feature for every row is recomputed from the offline event log as of
that row's timestamp, through the same `feature_value_as_of` the online path
uses.
"""

from __future__ import annotations

from compute import feature_value_as_of
from instaml.models import FeatureDefinition, TrainingRow
from offline import OfflineStore

RESERVED_COLUMNS = frozenset({"entity_id", "timestamp", "label"})


def build_training_set(
    rows: list[TrainingRow], features: list[FeatureDefinition], offline: OfflineStore
) -> list[dict[str, object]]:
    """One flat dict per input row, in input order: entity_id, timestamp,
    label, then one column per feature. Flat so `pandas.DataFrame(result)`
    just works.

    Cost is len(rows) * len(features) indexed DuckDB lookups. Fine at demo
    scale; a large backfill would want a single ASOF/window join in SQL
    instead (ROADMAP).
    """
    clashing = RESERVED_COLUMNS & {fd.name for fd in features}
    if clashing:
        raise ValueError(f"Feature name(s) clash with output columns: {', '.join(sorted(clashing))}")

    out: list[dict[str, object]] = []
    for row in rows:
        record: dict[str, object] = {
            "entity_id": row.entity_id,
            "timestamp": row.timestamp,
            "label": row.label,
        }
        for fd in features:
            record[fd.name] = feature_value_as_of(row.entity_id, fd, row.timestamp, offline)
        out.append(record)
    return out
