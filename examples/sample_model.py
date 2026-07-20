"""Sample model — reads features via the SDK to make a trivial decision.

Not a real model; proves the read path end-to-end: a caller asks for a
handful of features by name and gets back point-in-time values it can feed
into whatever scoring logic it wants.

Usage:
    python examples/quickstart.py     # seed some data first
    python examples/sample_model.py
"""

from __future__ import annotations

import os

import instaml

FEATURES = ["purchases_last_5m", "avg_cart_value_1h", "lifetime_total_spend"]


def should_offer_discount(entity_id: str) -> bool:
    """Toy rule: offer a discount to browsers who haven't converted recently
    but have spent meaningfully in the past — a "win back" heuristic."""
    values = instaml.get_features(entity_id, FEATURES)
    recent_purchases = values.get("purchases_last_5m") or 0
    lifetime_spend = values.get("lifetime_total_spend") or 0
    return recent_purchases == 0 and lifetime_spend > 50


def run() -> None:
    endpoint = os.environ.get("INSTAML_ENDPOINT", "http://localhost:8000")
    instaml.configure(endpoint=endpoint)
    for i in range(1, 11):
        entity_id = f"user_{i}"
        values = instaml.get_features(entity_id, FEATURES)
        decision = should_offer_discount(entity_id)
        print(f"{entity_id}: {values} -> offer_discount={decision}")


if __name__ == "__main__":
    run()
