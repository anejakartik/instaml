"""Turn one incoming event into updated feature values.

Recompute-on-write: every event triggers a re-aggregation over the matching
window of raw events (pulled from the OfflineStore), and the result overwrites
the OnlineStore's point value. Simpler and more obviously-correct than
maintaining incremental running aggregates per feature, at the cost of doing
more work per write — a fine trade-off at demo/indie-project event volumes,
and the same "correctness over cleverness" call tracelens's SQLite backend
makes by aggregating in Python instead of maintaining running counters.
"""

from __future__ import annotations

from datetime import datetime, timezone

from instaml.models import Aggregation, Event, FeatureDefinition, FeatureValue
from offline import OfflineStore
from online import OnlineStore


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def apply_event(
    event: Event,
    feature_defs: list[FeatureDefinition],
    online: OnlineStore,
    offline: OfflineStore,
) -> list[FeatureValue]:
    """Persist the event, recompute every feature it feeds, return what changed."""
    offline.append_event(event)

    updated: list[FeatureValue] = []
    for fd in feature_defs:
        if fd.source_event_type != event.event_type:
            continue
        window = fd.window_delta()
        since = None if window is None else utc_now() - window
        matching = offline.query_events(
            entity_id=event.entity_id, event_type=fd.source_event_type, since=since
        )
        value = _aggregate(matching, fd)
        now = utc_now()
        online.set(event.entity_id, fd.name, value, now)
        updated.append(
            FeatureValue(entity_id=event.entity_id, feature_name=fd.name, value=value, updated_at=now)
        )
    return updated


def _aggregate(events: list[Event], fd: FeatureDefinition) -> float:
    if fd.aggregation == Aggregation.COUNT:
        return float(len(events))

    if fd.field is None:
        raise ValueError(f"Feature {fd.name!r} uses {fd.aggregation.value} but has no `field` set")

    numeric = [
        v
        for e in sorted(events, key=lambda e: e.timestamp)
        if isinstance(v := e.payload.get(fd.field), (int, float))
    ]

    if fd.aggregation == Aggregation.SUM:
        return float(sum(numeric)) if numeric else 0.0
    if fd.aggregation == Aggregation.AVG:
        return float(sum(numeric) / len(numeric)) if numeric else 0.0
    if fd.aggregation == Aggregation.MIN:
        return float(min(numeric)) if numeric else 0.0
    if fd.aggregation == Aggregation.MAX:
        return float(max(numeric)) if numeric else 0.0
    if fd.aggregation == Aggregation.LAST:
        return float(numeric[-1]) if numeric else 0.0

    raise ValueError(f"Unhandled aggregation {fd.aggregation!r}")
