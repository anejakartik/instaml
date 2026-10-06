"""instaml — a real-time feature store you can deploy in a day.

Public API:
    instaml.configure(endpoint=...)
    instaml.emit_event(entity_id="user_42", event_type="purchase", payload={"amount": 19.99})
    instaml.get_features("user_42", ["purchases_last_5m", "avg_cart_value_1h"])

Design contracts:
- `emit_event` is fail-soft, same contract as tracelens's `@traced`: if the
  collector is unreachable, the caller's own code path is never interrupted.
- `get_features` is a synchronous read with a short timeout. On failure it
  logs and returns an empty dict rather than raising — a feature-store outage
  should degrade the caller's model to "no features", not crash it.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

import httpx

from .features import load_feature_defs
from .models import Aggregation, Event, FeatureDefinition, FeatureValue

log = logging.getLogger("instaml")

_endpoint: str = "http://localhost:8000"
_api_key: str | None = None
_print_local: bool = False
_async_post_threads: list[threading.Thread] = []


def configure(
    endpoint: str | None = None,
    api_key: str | None = None,
    print_local: bool | None = None,
) -> None:
    """Set the server endpoint and optional API key.

    `endpoint` defaults to INSTAML_ENDPOINT env var, then http://localhost:8000.
    """
    global _endpoint, _api_key, _print_local
    _endpoint = endpoint or os.environ.get("INSTAML_ENDPOINT") or "http://localhost:8000"
    _api_key = api_key or os.environ.get("INSTAML_API_KEY")
    if print_local is not None:
        _print_local = print_local


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if _api_key:
        headers["Authorization"] = f"Bearer {_api_key}"
    return headers


def emit_event(entity_id: str, event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Post one event in a background thread; never raises."""
    event = Event(entity_id=entity_id, event_type=event_type, payload=payload or {})
    if _print_local:
        log.info("event entity_id=%s type=%s payload=%s", entity_id, event_type, payload)

    def _send() -> None:
        try:
            httpx.post(
                f"{_endpoint.rstrip('/')}/events",
                json=event.model_dump(mode="json"),
                headers=_headers(),
                timeout=2.0,
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("instaml: event POST failed (fail-soft): %s", exc)

    th = threading.Thread(target=_send, daemon=True, name="instaml-emit")
    th.start()
    _async_post_threads.append(th)


def get_features(entity_id: str, feature_names: list[str]) -> dict[str, float | None]:
    """Synchronous read of the current feature values for one entity.

    Returns a dict of {feature_name: value}. On any failure (timeout, server
    down, unknown feature), logs and returns {} — callers should treat a
    missing key as "no signal" rather than distinguish failure modes here.
    """
    try:
        resp = httpx.get(
            f"{_endpoint.rstrip('/')}/features/{entity_id}",
            params={"names": ",".join(feature_names)},
            headers=_headers(),
            timeout=2.0,
        )
        resp.raise_for_status()
        return {fv["feature_name"]: fv["value"] for fv in resp.json()}
    except Exception as exc:  # noqa: BLE001
        log.warning("instaml: get_features failed (returning {}): %s", exc)
        return {}


__all__ = [
    "configure",
    "emit_event",
    "get_features",
    "load_feature_defs",
    "Aggregation",
    "Event",
    "FeatureDefinition",
    "FeatureValue",
]
__version__ = "0.1.0a1"
