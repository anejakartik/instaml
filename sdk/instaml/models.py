"""Shared data models for the SDK + server."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    """One raw event — the unit every feature is computed from."""

    id: UUID = Field(default_factory=uuid4)
    entity_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)


class Aggregation(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    LAST = "last"
    MIN = "min"
    MAX = "max"


class FeatureDefinition(BaseModel):
    """One declarative feature — loaded from a YAML feature-defs file.

    `window` is a duration string (`5m`, `1h`, `7d`) or the literal `lifetime`
    for an unbounded aggregate. `field` names the payload key to aggregate;
    unused for `count`, required for sum/avg/min/max/last.
    """

    name: str
    source_event_type: str
    aggregation: Aggregation
    field: str | None = None
    window: str = "lifetime"

    def window_delta(self) -> timedelta | None:
        """Parse `window` into a timedelta, or None for `lifetime` (unbounded)."""
        if self.window == "lifetime":
            return None
        unit = self.window[-1]
        amount = float(self.window[:-1])
        if unit == "m":
            return timedelta(minutes=amount)
        if unit == "h":
            return timedelta(hours=amount)
        if unit == "d":
            return timedelta(days=amount)
        if unit == "s":
            return timedelta(seconds=amount)
        raise ValueError(f"Unrecognized window unit in {self.window!r} (expected s/m/h/d suffix)")


class FeatureValue(BaseModel):
    """One computed feature value for one entity, as of `updated_at`."""

    entity_id: str
    feature_name: str
    value: float | None
    updated_at: datetime


class FeatureCatalogEntry(BaseModel):
    """A feature definition plus how many entities currently have a value —
    lets the dashboard show the catalog is real, not just declared."""

    definition: FeatureDefinition
    entity_count: int
