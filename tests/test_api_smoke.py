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
