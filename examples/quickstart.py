"""instaml quickstart — no Kafka/Redis required.

Emits synthetic e-commerce events (page views + purchases) across ~20 fake
users so you can see features update live without wiring up a real event
source.

Usage:
    docker compose up -d
    python examples/quickstart.py
    open http://localhost:8000
"""

from __future__ import annotations

import os
import random
import time

import instaml

USERS = [f"user_{i}" for i in range(1, 21)]
PRODUCTS = ["widget", "gadget", "doohickey", "gizmo", "thingamajig"]


def run() -> None:
    endpoint = os.environ.get("INSTAML_ENDPOINT", "http://localhost:8000")
    instaml.configure(endpoint=endpoint, print_local=True)
    print(f"Posting 60 synthetic events to {endpoint} …")

    for _ in range(60):
        user = random.choice(USERS)
        if random.random() < 0.4:
            amount = round(random.uniform(8.0, 220.0), 2)
            instaml.emit_event(
                entity_id=user,
                event_type="purchase",
                payload={"product": random.choice(PRODUCTS), "amount": amount},
            )
        else:
            instaml.emit_event(
                entity_id=user,
                event_type="page_view",
                payload={"page": random.choice(["home", "product", "cart", "checkout"])},
            )
        time.sleep(0.05)

    # Give the daemon threads a beat to flush.
    time.sleep(1.5)
    print(f"Done. Open {endpoint} to see the dashboard.")
    print(f"Try a lookup for one of: {', '.join(USERS[:5])}, ...")


if __name__ == "__main__":
    run()
