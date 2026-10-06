"""instaml server — FastAPI event ingest + feature read API + static dashboard.

Endpoints:
  POST /events                 — accept an Event, recompute every feature it feeds
  GET  /features/{entity_id}   — current value of one or more named features
  GET  /catalog                — every declared feature + how many entities have a value
  POST /training-set           — point-in-time-correct feature values for (entity, timestamp, label) rows
  GET  /health                 — online/offline backend descriptions
  GET  /                       — static HTML dashboard

Storage is pluggable on both sides — see server/online/ and server/offline/.
  INSTAML_ONLINE_URL   memory:// (default, local dev) | redis://...  (hosted demo)
  INSTAML_OFFLINE_PATH path to a DuckDB file (default ./instaml.duckdb)
  INSTAML_FEATURES_PATH path to the feature-defs YAML (default ./features/demo.yaml)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Make `sdk` importable for shared models + feature-def loading.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from compute import apply_event  # noqa: E402
from instaml.features import load_feature_defs  # noqa: E402
from instaml.models import Event, FeatureCatalogEntry, FeatureValue, TrainingSetRequest  # noqa: E402
from offline import make_offline_store  # noqa: E402
from online import make_online_store
from training import build_training_set  # noqa: E402

ONLINE_URL = os.environ.get("INSTAML_ONLINE_URL", "memory://")
OFFLINE_PATH = os.environ.get("INSTAML_OFFLINE_PATH", "./instaml.duckdb")
FEATURES_PATH = os.environ.get(
    "INSTAML_FEATURES_PATH", str(Path(__file__).resolve().parents[1] / "features" / "demo.yaml")
)

online = make_online_store(ONLINE_URL)
offline = make_offline_store(OFFLINE_PATH)
feature_defs = load_feature_defs(FEATURES_PATH)
feature_defs_by_name = {fd.name: fd for fd in feature_defs}


app = FastAPI(
    title="instaml",
    version="0.1.0",
    description="Real-time feature store you can deploy in a day",
)

_cors_origins = os.environ.get("INSTAML_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    online.init()
    offline.init()


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "online": online.describe(),
        "offline": offline.describe(),
        "feature_count": len(feature_defs),
    }


# ---- Ingest -----------------------------------------------------------------


@app.post("/events", response_model=list[FeatureValue])
def ingest_event(event: Event) -> list[FeatureValue]:
    """Persist the event and return every feature value it updated."""
    return apply_event(event, feature_defs, online, offline)


# ---- Read ---------------------------------------------------------------


@app.get("/features/{entity_id}", response_model=list[FeatureValue])
def get_features(
    entity_id: str,
    names: str = Query(..., description="Comma-separated feature names"),
) -> list[FeatureValue]:
    requested = [n.strip() for n in names.split(",") if n.strip()]
    unknown = [n for n in requested if n not in feature_defs_by_name]
    if unknown:
        raise HTTPException(404, f"Unknown feature(s): {', '.join(unknown)}")

    out: list[FeatureValue] = []
    for name in requested:
        hit = online.get(entity_id, name)
        if hit is None:
            out.append(FeatureValue(entity_id=entity_id, feature_name=name, value=None, updated_at=_epoch()))
        else:
            value, updated_at = hit
            out.append(FeatureValue(entity_id=entity_id, feature_name=name, value=value, updated_at=updated_at))
    return out


@app.get("/catalog", response_model=list[FeatureCatalogEntry])
def catalog() -> list[FeatureCatalogEntry]:
    return [
        FeatureCatalogEntry(definition=fd, entity_count=online.entity_count(fd.name))
        for fd in feature_defs
    ]


# ---- Training data ----------------------------------------------------------


@app.post("/training-set")
def training_set(request: TrainingSetRequest) -> list[dict[str, object]]:
    """Feature values for each row as of that row's timestamp, recomputed
    from the offline event log, never the current online value, so labels
    can't be joined against features from their own future."""
    unknown = [n for n in request.features if n not in feature_defs_by_name]
    if unknown:
        raise HTTPException(404, f"Unknown feature(s): {', '.join(unknown)}")
    try:
        return build_training_set(
            request.rows, [feature_defs_by_name[n] for n in request.features], offline
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _epoch():
    from datetime import datetime, timezone

    return datetime.fromtimestamp(0, tz=timezone.utc)


# ---- Static dashboard ----------------------------------------------------


_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(str(_STATIC_DIR / "index.html"))

else:

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "instaml",
            "version": "0.1.0",
            "docs": "/docs",
            "github": "https://github.com/anejakartik/instaml",
        }
