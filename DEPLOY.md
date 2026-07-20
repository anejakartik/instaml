# Deploy instaml — server to Fly.io, domain via Vercel

> Outcome: `instaml.kartikaneja.com` is a live, clickable demo. Same
> split-host pattern as tracelens: Fly.io runs the stateful FastAPI + DuckDB
> server, Vercel is a pure rewrite-proxy for the custom domain (no separate
> frontend build — the dashboard is server-rendered static HTML).

---

## Step 1 — Deploy the server to Fly.io

`fly.toml` at the repo root is already configured: DuckDB on a persistent
volume, in-memory online store by default (upgrade to Redis below), HTTPS
forced, auto-stop when idle.

```bash
cd ~/github/instaml

# One-time setup. Accept the default name (or pick your own — fly will
# tell you if "instaml-kartik" is taken).
flyctl launch --copy-config --no-deploy

# Create the persistent volume for the DuckDB event log
flyctl volume create instaml_data --region iad --size 1 --yes

# First deploy
flyctl deploy

# Verify health
flyctl status
curl https://<your-fly-app>.fly.dev/health
# Expected: {"ok":true,"online":"memory (...)","offline":"duckdb (...)","feature_count":6}
```

### Optional — upgrade the online store to Redis (Upstash free tier)

The in-memory online store is fine for a single always-on machine, but it
resets on every redeploy/restart and can't be shared if you ever scale past
one instance. To make it durable:

1. Create a free Redis database at https://console.upstash.com
2. Copy its connection URL (starts with `redis://` or `rediss://`)
3. `flyctl secrets set INSTAML_ONLINE_URL=redis://default:<password>@<host>:<port>`
4. `flyctl deploy` again to pick up the secret

### Seed demo data (one-time)

```bash
INSTAML_ENDPOINT=https://instaml-kartik.fly.dev python3 examples/quickstart.py
```

This posts 60 synthetic e-commerce events across 20 fake users so the
dashboard isn't an empty state for visitors.

---

## Step 2 — Import to Vercel (proxy only, no build)

Same as tracelens — no separate frontend, so this is a pure rewrite-proxy.

1. Open https://vercel.com/new
2. Click "Import" next to `anejakartik/instaml`
3. **Root Directory:** leave as repo root
4. **Framework Preset:** "Other" — `vercel.json` handles everything
5. Click **Deploy**

---

## Step 3 — Custom domain: instaml.kartikaneja.com

In the Vercel project for `instaml`:

1. **Settings → Domains → Add** → enter `instaml.kartikaneja.com`
2. Vercel shows a DNS record to add at your registrar:
   - **Type:** CNAME
   - **Name:** `instaml`
   - **Value:** `cname.vercel-dns.com`
3. Add that record (same place you added `tracelens`/`evalstack`)
4. Back in Vercel, click "Refresh" — SSL cert auto-provisions once DNS propagates

Verify:

```bash
curl -I https://instaml.kartikaneja.com
# Expected: HTTP/2 200, x-vercel-id: ...
```

---

## Step 4 — Link from the portfolio + READMEs

After the domain is live:

1. **Update instaml/README.md** — replace `*(coming soon)*` with the live link
2. **Update portfolio-site** — add a "View live →" link to the instaml project card on `/projects`, following the same pattern as tracelens/evalstack
3. **LinkedIn Featured carousel** — add "Live demo: instaml.kartikaneja.com"

---

## Cost expectations

Same as the other flagship projects: Fly.io free tier + Vercel Hobby free
tier + Upstash Redis free tier (if you set it up) = $0/mo.

---

## Troubleshooting

**Fly server returns 502**: machine cold-starting after idle auto-stop.
First request takes 1–3s.

**Vercel shows a 404**: confirm `vercel.json` is at the repo root and the
Vercel project's Root Directory is the repo root.

**DuckDB data gone after redeploy**: confirm the volume is mounted —
`flyctl volumes list` should show `instaml_data`. If not, repeat the
`flyctl volume create` step.

**Custom domain stuck at "Invalid Configuration"**: DNS hasn't propagated —
`dig instaml.kartikaneja.com CNAME +short` should return `cname.vercel-dns.com`.
