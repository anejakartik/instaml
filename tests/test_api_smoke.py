"""End-to-end API smoke tests over a real TestClient — memory online store,
a fresh temp DuckDB offline store, the real demo.yaml feature defs.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "sdk"))
sys.path.insert(0, str(_ROOT / "server"))

os.environ["INSTAML_ONLINE_URL"] = "memory://"
os.environ["INSTAML_OFFLINE_PATH"] = tempfile.mktemp(suffix=".duckdb")
os.environ["INSTAML_FEATURES_PATH"] = str(_ROOT / "features" / "demo.yaml")

import main  # noqa: E402, PLC0415
from fastapi.testclient import TestClient  # noqa: E402


def test_health() -> None:
    with TestClient(main.app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["feature_count"] >= 4


def test_catalog_lists_declared_features_with_zero_entities_initially() -> None:
    with TestClient(main.app) as c:
        r = c.get("/catalog")
        assert r.status_code == 200
        rows = r.json()
        names = {row["definition"]["name"] for row in rows}
        assert "purchases_last_5m" in names


def test_post_event_then_read_features() -> None:
    with TestClient(main.app) as c:
        r = c.post(
            "/events",
            json={"entity_id": "test_user", "event_type": "purchase", "payload": {"amount": 25.0}},
        )
        assert r.status_code == 200
        updated = r.json()
        updated_names = {fv["feature_name"] for fv in updated}
        assert "purchases_last_5m" in updated_names
        assert "lifetime_total_spend" in updated_names

        r2 = c.get("/features/test_user", params={"names": "purchases_last_5m,lifetime_total_spend"})
        assert r2.status_code == 200
        rows = {row["feature_name"]: row["value"] for row in r2.json()}
        assert rows["purchases_last_5m"] == 1.0
        assert rows["lifetime_total_spend"] == 25.0


def test_get_features_unknown_name_returns_404() -> None:
    with TestClient(main.app) as c:
        r = c.get("/features/test_user", params={"names": "not_a_real_feature"})
        assert r.status_code == 404


def test_get_features_for_entity_with_no_events_returns_null_values() -> None:
    with TestClient(main.app) as c:
        r = c.get("/features/brand_new_user", params={"names": "purchases_last_5m"})
        assert r.status_code == 200
        rows = r.json()
        assert rows[0]["value"] is None


def test_dashboard_root_serves_html() -> None:
    with TestClient(main.app) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert "instaml" in r.text


def test_training_set_is_point_in_time_correct() -> None:
    with TestClient(main.app) as c:
        base = "2026-09-01T12:00:00+00:00"
        for ts in ("2026-09-01T12:00:00Z", "2026-09-01T12:10:00Z", "2026-09-01T12:20:00Z"):
            c.post("/events", json={"entity_id": "pit_user", "event_type": "purchase", "timestamp": ts,
                                    "payload": {"amount": 10}})
        r = c.post(
            "/training-set",
            json={
                "rows": [
                    {"entity_id": "pit_user", "timestamp": "2026-09-01T12:15:00Z", "label": 1},
                    {"entity_id": "pit_user", "timestamp": base, "label": 0},
                ],
                "features": ["lifetime_purchase_count", "lifetime_total_spend"],
            },
        )
        assert r.status_code == 200
        first, second = r.json()
        assert (first["lifetime_purchase_count"], first["lifetime_total_spend"], first["label"]) == (2.0, 20.0, 1)
        assert second["lifetime_purchase_count"] == 1.0


def test_training_set_unknown_feature_is_404() -> None:
    with TestClient(main.app) as c:
        r = c.post("/training-set", json={"rows": [{"entity_id": "u", "timestamp": "2026-09-01T00:00:00Z"}],
                                          "features": ["nope"]})
        assert r.status_code == 404


def test_training_set_requires_at_least_one_feature() -> None:
    with TestClient(main.app) as c:
        r = c.post("/training-set", json={"rows": [], "features": []})
        assert r.status_code == 422


def test_feature_values_survive_a_restart() -> None:
    from online import make_online_store

    with TestClient(main.app) as c:
        c.post("/events", json={"entity_id": "restart_user", "event_type": "purchase", "payload": {"amount": 5}})

    main.online = make_online_store("memory://")  # what a reboot does to the in-memory store
    with TestClient(main.app) as c:
        r = c.get("/features/restart_user", params={"names": "lifetime_purchase_count"})
        assert r.json()[0]["value"] == 1.0
