# Demo — instaml

## Live demo

**URL:** [instaml.kartikaneja.com](https://instaml.kartikaneja.com)

**Hosting:**
- Domain: Vercel (pure rewrite-proxy, no separate frontend build)
- Backend: Fly.io (FastAPI + DuckDB on a persistent volume)
- Online store: in-memory by default, upgradeable to Upstash Redis free tier
- Cost: **free tier** across the board

If the demo is sleeping (Fly.io free tier auto-stops when idle), first request may take 2–3 seconds.

## What to try

1. Open the dashboard — the feature catalog shows 6 declared features with live entity counts
2. Type an entity id from the seeded demo data (e.g. `user_1` through `user_20`) into the lookup box
3. Click "Look up" — see that entity's current feature values (purchase counts, cart value averages, lifetime spend) as of right now

## Screenshots

See `docs/screenshots/` once captured from the live deploy (README/DEMO get updated with the real link once `instaml.kartikaneja.com` is up — see DEPLOY.md).

## Local fallback

If the demo URL is down (or you want to try with your own data):

```bash
git clone https://github.com/anejakartik/instaml.git
cd instaml
pip install -e ./sdk
docker compose up -d
python examples/quickstart.py
open http://localhost:8000
```

## Quick port-forward demo (during a live conversation)

If you want to show your local dev environment to someone remote:

```bash
# Cloudflare Tunnel (recommended, free, named domains)
cloudflared tunnel --url http://localhost:8000

# OR ngrok (free, random URL)
ngrok http 8000
```

## Demo data + reset

- Demo data is whatever's been posted via `examples/quickstart.py` — no automatic reset
- No real user data — safe to throw arbitrary synthetic events at it
- If you need persistent storage for real use, self-host with the `INSTAML_OFFLINE_PATH` volume mounted
