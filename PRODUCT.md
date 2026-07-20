# Product — instaml

> The "why" behind this repo. Read first if you're an AI agent contributing.

## Target user

**Persona:** ML Engineer at a Series-A startup (5–30 person eng team). Has a model — recommendation, fraud, personalization — and needs real-time features to serve it.

**Job they're trying to do:** Get fresh, correct feature values into a model at serving time, without spending a sprint on infrastructure.

**Current workflow:** Hand-rolled Redis writes scattered across the codebase, a cron job that recomputes aggregates into Postgres, and no single place that says what a feature actually means or how fresh it is.

## The pain

1. **Feast deployment is days of work.** Kubernetes, a registry service, a materialization job — overkill before you have the team to own it.
2. **Tecton is enterprise-priced and enterprise-shaped.** Built for platform teams with a dedicated feature-store owner, not a 2-person ML team.
3. **The DIY path rots fast.** Feature logic ends up duplicated between the write path and the read path, with no single source of truth for "what does `purchases_last_5m` actually mean."

What it costs them: engineering time that should go into the model, and silent correctness bugs when the online and offline computations of the "same" feature quietly diverge.

## Existing alternatives — and why they fall short

| Alternative | What it does | Why it doesn't fit this persona |
|---|---|---|
| **Feast** | Open-source feature store, full online/offline split | Real deployment (registry service, materialization jobs, infra) is a multi-day project |
| **Tecton** | Managed feature platform | Enterprise pricing and onboarding — built for teams with a dedicated platform owner |
| **Status quo: DIY Redis + cron** | Hand-rolled online writes, batch offline recompute | Feature logic duplicated between paths, no declared feature catalog, drift risk |

## Our wedge

- **One YAML file declares every feature** — name, source event, aggregation, window. No duplicated logic between online and offline paths, because both read the same definition.
- **Recompute-on-write, not two separate pipelines** — the value written to the online store and the value derivable from the offline log are always the same computation, run at write time.
- **Free + self-hostable** — DuckDB + in-memory (or Redis free tier) means zero infra cost to try it.

## MVP scope (what we shipped first)

**Must-have:**
- YAML feature definitions with count/sum/avg/min/max/last aggregations over rolling or lifetime windows
- `POST /events` ingest → DuckDB append + online-store recompute for every matching feature
- `GET /features/{entity_id}` — point-in-time read of the latest computed values
- `GET /catalog` — every declared feature + how many entities currently have a value
- Python SDK (`emit_event`, `get_features`) with the same fail-soft philosophy as tracelens
- Live dashboard, synthetic demo data generator

**Out of scope for MVP** (see [ROADMAP.md](./ROADMAP.md)):
- Real Kafka ingestion (HTTP `POST /events` is the primary path; Kafka is an optional adapter)
- Point-in-time-correct training-dataset export (training/serving skew prevention)
- Feature versioning / definition history

## Success metric

- Live demo at `instaml.kartikaneja.com` showing features updating from synthetic traffic
- A `docker compose up` → working dashboard in under 60 seconds, no external service required

## What success looks like in 6 months

- Closes the ML Eng lane gap in the flagship-project portfolio, cited in interviews alongside evalstack/tracelens/routerai
- At least one real (non-synthetic) integration — e.g. instaml feeding a routerai routing decision

## Non-goals

- Compete with Feast/Tecton on enterprise features (multi-tenant registries, RBAC, SLAs)
- Distributed feature computation across multiple services — single-service scale only
- Streaming joins across multiple event types into one feature — each feature has exactly one `source_event_type`
