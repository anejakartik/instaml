# Roadmap — instaml

> Updated weekly. Add a dated entry per shipped feature. Feeds the content engine — each `[x]` is a potential LinkedIn post.

## Shipping log (newest on top)

### 2026-10-06 — point-in-time training sets, CI green again
- [x] `POST /training-set` + `instaml.get_training_set()`: features for `(entity_id, timestamp, label)` rows computed from events at or before each row's timestamp (offline store gained an `until` bound)
- [x] One `feature_value_as_of()` now serves both the online write path (as_of=now) and training export (as_of=row time), so there's no second implementation to drift into training/serving skew
- [x] `examples/leakage_demo.py`: 500 synthetic users, label = "bought within 14 days of the snapshot". `lifetime_purchase_count` alone scores AUC 0.899 with a naive join against current values vs 0.795 point-in-time (0.08–0.10 gap across 6 seeds); 322/500 rows had a leaked value
- [x] Fixed: non-UTC event timestamps were relabelled, not converted (12:00+05:30 was stored as 12:00 UTC, 5.5h off), skewing every window for any client not sending UTC
- [x] Fixed: CI red since 2026-08-11. There was no ruff config and ruff was unpinned in CI, so a ruff release changing the default rules failed the lint gate with no code change. Added `ruff.toml` (same rule set as evalstack/tracelens) and pinned ruff
- [x] 43 tests
- Notes: export does len(rows) × len(features) indexed DuckDB lookups, fine at demo scale. A large backfill wants one ASOF join in SQL; added below.

### 2026-07-20 — Alpha MVP: declarative features, dual-write, SDK, dashboard
- [x] YAML feature definitions (count/sum/avg/min/max/last, rolling or lifetime window)
- [x] FastAPI server: `POST /events`, `GET /features/{entity_id}`, `GET /catalog`, `GET /health`
- [x] Pluggable online store: in-memory (default) + Redis (`INSTAML_ONLINE_URL`)
- [x] DuckDB offline store — indexed event log, Parquet export
- [x] Python SDK: fail-soft `emit_event`, degrade-to-`{}` `get_features`
- [x] Static dashboard: live feature catalog + entity lookup
- [x] Synthetic demo generator (`examples/quickstart.py`) + a toy read-path model (`examples/sample_model.py`)
- [x] 30 passing tests: aggregation math, online/offline store round-trips, API smoke tests
- Notes: recompute-on-write (re-aggregate from the offline log on every event) instead of maintaining running counters — simpler and obviously-correct at demo/indie event volumes, same trade-off tracelens's SQLite backend makes.

<!-- copy the block above for each new week -->

---

## Short-term — next 4 weeks

Priority order. Pick from top of list.

- [ ] **P0 / Fly.io + Vercel deploy** — get `instaml.kartikaneja.com` live, seed with synthetic traffic *(est. 1 day · drives a build-in-public post)*
- [ ] **P0 / Kafka ingestion adapter** — optional consumer that forwards Upstash Kafka messages into the same `/events` handler
- [ ] **P1 / Feature drift monitoring** — flag when a feature's distribution shifts week-over-week
- [x] **P1 / Point-in-time training-dataset export**: shipped 2026-10-06 (see above)
- [ ] **P2 / Single-SQL ASOF join for training sets**: replace the per-row lookups with one DuckDB window/ASOF query for large backfills
- [ ] **P2 / Feature lineage UI** — which events feed which features, visualized

## Medium-term — months 2–3

Themes, not features. Crystallize into P0/P1 when we get there.

- [ ] SQL-based feature definitions (not just YAML aggregations) for more complex logic
- [ ] Multi-event-type joins into one feature (e.g. "purchases minus refunds")
- [ ] Feature catalog search + tagging
- [ ] Cost dashboard (storage + read volume)

## Long-term — 6+ months

- [ ] Real integration with routerai (route on a feature-derived cost/risk signal)
- [ ] Multi-tenant orgs + API keys

## Stretch / blue-sky

- A `instaml diff` CLI that shows what changes if you edit a feature definition, before you deploy it
- Backfill CLI: recompute a feature's history from the offline log after adding it

---

## Content posts derived from this roadmap

Each shipped feature should produce a post. Track them here so we don't double-post:

| Feature | Post draft | Posted? | URL |
|---|---|---|---|
| Alpha MVP launch | — | — | — |
| Point-in-time training sets | portfolio-site/docs/brand-plan/profile/linkedin-post-2026-10-13-instaml-pit.md | — | — |

## Decisions log

Why we built X this way (avoid re-litigating same arguments):

- **2026-07-20** — chose DuckDB over literal per-row Parquet appends for the offline store, because Parquet has no efficient native append operation; DuckDB gives fast native inserts *and* `COPY TO ... FORMAT PARQUET` for portable snapshots. See `docs/architecture.md`.
- **2026-07-20** — chose recompute-on-write over incremental running aggregates, for correctness-by-construction over a small performance win at this scale.
- **2026-07-20** — created a fresh `instaml` repo instead of repurposing the old `streamstage` repo (unrelated May-2026 CDC-demo content that never became this project — that idea shipped separately as `lakehouseit`).
