# Phase 6B Automation Audit

- Audit date: 2026-07-10
- Scope: git/deployment state before building the matchday automation workflow.

## Git state (verified)

- Branch: `main`; commit at audit time: `efa514a`; working tree clean.
- **No GitHub remote configured** — pushing to GitHub remains a manual user step (no URL is invented anywhere).
- Tracked generated outputs: `public_data/` (13 JSON), `outputs/live_state/` (62 files incl. histories, manifests, normalized provider CSVs, sanitized snapshots), `outputs/models/` (4), `outputs/reports/` (107), `outputs/simulations/` (6), plus `data/processed` and `data/features`. `website/package-lock.json` is committed (enables `npm ci` in CI).
- Ignored (verified with `git check-ignore`): `.env`, `website/node_modules/`, `website/.next/`, `data/backups/`, kaggle credentials.

## Pre-existing GitHub Actions (finding)

`.github/workflows/update_data.yml` (Phase 2 era) ran `update --mode matchday` on a **daily 23:00 UTC cron**, wrote secrets into a `.env` file on the runner, predated the football-data.org provider (only `API_FOOTBALL_KEY`), ran no forecast, no validation gating, and published nothing (artifacts only). This conflicts with the Phase 6B rules (no blind provider cron; no invalid-forecast publication path; prefer env-var secrets over files). **Removed** and replaced by `validate.yml` (offline, secret-free) and `portfolio-refresh.yml` (manual dispatch, gated).

## What actually needs committing after a matchday forecast

A matchday refresh dirties ~4 categories of tracked files:

1. **Publishable (allowlist)** — `public_data/*.json`; forecast/source history CSVs; `latest_live_run_manifest.json`, `tournament_phase_transition.json`, `live_provider_freshness.json`, `live_forecast_summary.json`, `live_forecast_quality_gate.json`; current forecast CSVs (champion/reach-final/pairs/predictions/matchups); normalized provider CSVs + merged bracket; the portfolio refresh manifest.
2. **Expected volatile, not auto-committed** — `data/processed/*`, `data/features/*`, remaining `outputs/*` (reports contain machine-local absolute paths; regenerate deterministically).
3. **Forbidden always** — `.env`, credentials, `provider_snapshots/` (sanitized but raw payloads), `api_football_live_*.json`, node_modules/.next.
4. **Anything else changed → automation stops** (source, website, dashboard, docs are never auto-committed).

Implemented as `COMMIT_ALLOWLIST` / `EXPECTED_VOLATILE` / `FORBIDDEN` in `src/public_export/commit_safety.py`, exercised by `python main.py check-commit-safety` and the Actions gate, and covered by tests.

## Frontend deployment compatibility (verified)

- **Website:** fully static Next.js; `lib/data.ts` reads `../public_data/*.json` at build time with `fs`. Vercel clones the entire repository even when Root Directory is `website`, so the relative read works in Vercel builds exactly as it does locally (re-verified with `npm run lint` + `npm run build`: 55 static pages). No runtime data access, no provider key, no prebuild sync needed.
- **Dashboard:** `dashboard/app.py` resolves paths from its own file location (`Path(__file__).parents[2]`), so the working directory does not matter; reads only committed `public_data/` + `outputs/live_state/` artifacts; no API calls; missing files degrade to notices; no secrets required (verified via headless startup + `validate-dashboard`).
- **Runtime secrets required by public frontends: none.** Only the forecasting workflow itself needs `FOOTBALL_DATA_ORG_KEY`.

## Publication-safety gap found and closed

Before 6B, the pipeline rebuilt `public_data/` in place without validating first — a bad build could have replaced good public data. Now `src/public_export/publish.py` builds exports into a staging directory, validates them there, and only promotes on pass; rejects preserve the previous known-good dataset (tested).

## Known limitations

- Many tracked `outputs/reports/*.md` files (from earlier phases) embed absolute local paths; they are excluded from the automation allowlist but remain in git history from the initial commit. Cosmetic; consider relativizing report writers later.
- `validate.yml` runs against committed artifacts; it validates state consistency, not provider connectivity (by design).
