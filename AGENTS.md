# AGENTS.md — instructions for AI coding agents

> If you're an AI agent (Claude Code, OpenAI Codex, Cursor agent, etc.) working on this repo, read this first.

## Before you touch code

1. Read [PRODUCT.md](./PRODUCT.md) — understand the user/problem before suggesting features.
2. Read the top section of [ROADMAP.md](./ROADMAP.md) — what's actually prioritized right now.
3. Check open issues and existing PRs to avoid duplicating work.

## Coding conventions

- **Python:** type hints required (`from __future__ import annotations` at the top of every module), `ruff` clean, `pytest` for tests
- Prefer small, focused PRs over sweeping changes
- Match existing patterns — the `Storage`-Protocol pattern from `server/online/` and `server/offline/` is deliberate (mirrors tracelens's pluggable-backend design); don't collapse it into a single concrete class
- Avoid speculative generality (no "we might need this later")

## What to focus on

| You should | You should not |
|---|---|
| Fix bugs, improve docs, polish UX | Add features not in ROADMAP without asking |
| Add tests for the code you write | Add tests for un-related code unless asked |
| Update ROADMAP.md when you ship | Refactor for refactoring's sake |
| Write a `## YYYY-MM-DD — title` shipping-log entry in ROADMAP.md when you ship | Skip docs for "obvious" changes |

## Commits & PRs

- **Commit messages:** imperative mood, focused on *why*. Example: `Fix DuckDB COPY parameterization for export_parquet`
- **PR descriptions:** brief — problem in 1–2 lines, change in 2–3 lines, test plan in bullets
- **Squash on merge** — keeps history readable

## Things that will get a PR rejected

- Unjustified abstraction layers
- Vendor lock-in we didn't agree to
- Dependency additions without rationale
- Logic changes without tests
- Comments that restate what code does
- Skipping pre-commit hooks (`--no-verify`)
- Changes that break the live demo deployment
- Bypassing the `OnlineStore`/`OfflineStore` Protocol abstraction with backend-specific code in `server/main.py` or `server/compute.py`

## How this repo deploys

- **CI:** `.github/workflows/ci.yml` runs the test suite on every push
- **Deploy:** manual `flyctl deploy` (see [DEPLOY.md](./DEPLOY.md)) — no auto-deploy workflow yet
- **Live demo:** instaml.kartikaneja.com
- **Cost discipline:** demo lives on free tier (Fly.io + Vercel + Upstash Redis); if a change moves a workload to paid tier, flag it explicitly

## Where to ask questions

- Open an issue with `[question]` prefix
- Read [docs/architecture.md](./docs/architecture.md) for the why behind architectural choices

## Companion document

- [.github/copilot-instructions.md](./.github/copilot-instructions.md) — same intent, formatted for GitHub Copilot's custom-instructions system
