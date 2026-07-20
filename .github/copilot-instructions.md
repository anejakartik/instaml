# Copilot instructions for instaml

> Same intent as [../../AGENTS.md](../AGENTS.md) but in the Copilot custom-instructions format. GitHub Copilot reads this file automatically.

## Product context

This repo is **instaml** — a real-time feature store you can deploy in a day. The full positioning is in [PRODUCT.md](../PRODUCT.md).

Target user: **ML Engineer at a Series-A startup who needs real-time features and doesn't have weeks for a Feast deployment**.
Their pain: **Feast is days of infra work, Tecton is enterprise-priced, DIY Redis+cron duplicates feature logic and drifts**.
Our wedge: **one YAML file declares every feature; both online and offline paths read the same definition, computed at write time**.

## Code style

- Python: type hints (`from __future__ import annotations`), ruff, pytest
- Prefer small focused changes
- Match the existing `Storage`-Protocol pattern in `server/online/` and `server/offline/` — don't introduce new abstractions without justification
- No speculative generality

## When suggesting code

**Do:**
- Match the conventions in `sdk/instaml/`, `server/`, and `tests/`
- Add type hints + tests alongside any new logic
- Update [ROADMAP.md](../ROADMAP.md) shipping-log when shipping a roadmap item
- Use the libraries already in `server/requirements.txt` / `sdk/pyproject.toml` — don't introduce new deps without flagging

**Don't:**
- Add features not on the active roadmap without asking
- Restate what code does in comments
- Add backwards-compat shims for code that doesn't exist yet
- Skip pre-commit hooks
- Put backend-specific logic (Redis/DuckDB details) anywhere outside `server/online/` / `server/offline/`

## Repo layout

```
instaml/
├── README.md, PRODUCT.md, ROADMAP.md, AGENTS.md, DEMO.md, DEPLOY.md
├── .github/         # CI, copilot-instructions
├── docs/
│   └── architecture.md
├── sdk/instaml/      # Python SDK: configure, emit_event, get_features, feature-def loader
├── server/           # FastAPI app, compute.py, online/, offline/, static dashboard
├── features/         # demo.yaml — sample feature definitions
├── examples/         # quickstart.py (synthetic event generator), sample_model.py
└── tests/
```

## Deployment

- CI: `.github/workflows/ci.yml` runs the test suite
- Deploy: manual `flyctl deploy` — see [DEPLOY.md](../DEPLOY.md)
- Live demo: **instaml.kartikaneja.com** — stays on free tier
- A change that pushes the workload to paid tier should call this out in the PR

## Companion docs

- [PRODUCT.md](../PRODUCT.md) — user/problem/solution
- [ROADMAP.md](../ROADMAP.md) — what's next
- [AGENTS.md](../AGENTS.md) — full agent guide (read this if you're a more general agent like Claude Code or Codex)
