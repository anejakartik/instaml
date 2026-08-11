# instaml — a real-time feature store you can deploy in a day

> Feast and Tecton are built for platform teams with weeks to spend on deployment. instaml is a YAML feature-defs → online/offline dual-write feature store a solo ML engineer can stand up before lunch.

**Live demo:** [instaml.kartikaneja.com](https://instaml.kartikaneja.com)
**Status:** alpha · last shipped 2026-07-20
**Built by:** [Kartik Aneja](https://kartikaneja.com) — AI/ML Platform Engineer

---

## Why this exists

See [PRODUCT.md](./PRODUCT.md) for the full user/problem/solution writeup. TL;DR:

- **Who:** ML Engineer at a Series-A startup with a model that needs real-time features and no time for a Feast deployment
- **Pain:** Feast is days of infra work; Tecton is enterprise-priced; most teams end up with hand-rolled Redis + Postgres + brittle backfill scripts
- **Why now:** Real-time ML is mainstream now, but the feature-platform layer underneath it is still either too heavy or too improvised

## What works today (alpha MVP)

- **Declarative YAML feature definitions** — `count` / `sum` / `avg` / `min` / `max` / `last`, over a rolling window (`5m`, `1h`, `7d`) or `lifetime`
- **Dual-write on every event** — DuckDB stores every raw event (the offline source of truth, exportable to Parquet); an online store (in-memory or Redis) holds the current computed value per entity for fast reads
- **Python SDK** — `instaml.emit_event(...)` (fail-soft, never breaks your app) and `instaml.get_features(...)` (degrades to `{}` on outage, never raises)
- **Live dashboard** — feature catalog + an entity lookup panel, auto-refreshing
- **No-key quickstart** — `examples/quickstart.py` posts 60 synthetic e-commerce events across 20 fake users so the dashboard isn't empty

## Try it (60 seconds, local)

```bash
git clone https://github.com/anejakartik/instaml.git
cd instaml
pip install -e ./sdk
docker compose up -d
python examples/quickstart.py
open http://localhost:8000
```

Real usage:

```python
import instaml

instaml.configure(endpoint="http://localhost:8000")

# From your event-producing code:
instaml.emit_event(entity_id="user_42", event_type="purchase", payload={"amount": 19.99})

# From your model-serving code:
features = instaml.get_features("user_42", ["purchases_last_5m", "avg_cart_value_1h"])
```

## Architecture

See [docs/architecture.md](./docs/architecture.md). Stack: Python SDK + FastAPI server + DuckDB offline store (Parquet-exportable) + pluggable online store (in-memory or Redis), deployed on Fly.io + Vercel.

## What's next

See [ROADMAP.md](./ROADMAP.md). Top items: Kafka ingestion adapter, feature drift monitoring, point-in-time-correct training-dataset export, feature lineage UI.

## Contributing

PRs welcome. See [AGENTS.md](./AGENTS.md).

## License

MIT — see [LICENSE](./LICENSE).
