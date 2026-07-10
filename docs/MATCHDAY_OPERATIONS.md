# Matchday Operations

How to refresh the public forecast after a real FIFA 2026 match completes. Four things are distinct and are reported separately — a success at one level never implies the next:

1. **Analytical forecast succeeded** — the pipeline produced a validated forecast (`live_forecast_status: success`).
2. **Public export succeeded** — staged exports passed validation and replaced `public_data/` (`public_export_publication: published`). On failure the previous known-good `public_data/` is preserved automatically.
3. **Git commit succeeded** — allowlisted artifacts were committed after commit-safety checks.
4. **Deployment succeeded** — Vercel/Streamlit rebuilt from the pushed commit (their dashboards confirm this, not this repo).

## Local workflow (recommended)

```bash
git pull
python main.py refresh-portfolio --n-simulations 10000 --no-retrain
```

The command exits non-zero and prints `NOT eligible for publication` when a critical validation failed — in that case do not commit public updates; inspect `outputs/reports/portfolio/latest_portfolio_refresh_manifest.json` and the validation reports.

When eligible:

```bash
python main.py check-commit-safety     # classifies changed files; fails on unexpected ones
git status
git diff --stat
git add public_data outputs/live_state/*_history.csv outputs/live_state/latest_live_run_manifest.json \
        outputs/live_state/tournament_phase_transition.json outputs/live_state/live_provider_freshness.json \
        outputs/live_state/live_forecast_summary.json outputs/live_state/live_forecast_quality_gate.json \
        outputs/live_state/live_champion_probabilities.csv outputs/live_state/team_reach_final_probabilities.csv \
        outputs/live_state/finalist_pair_probabilities.csv outputs/live_state/live_knockout_match_predictions.csv \
        outputs/live_state/remaining_known_knockout_matchups.csv outputs/live_state/football_data_org_*_normalized.csv \
        outputs/live_state/merged_bracket_state.csv outputs/reports/portfolio/latest_portfolio_refresh_manifest.json
git commit -m "Update live FIFA 2026 forecast after completed match"
git push
```

Vercel redeploys the website from the push; Streamlit Cloud reads the newest repository outputs.

## GitHub Actions workflow (manual dispatch)

`Actions → Portfolio Refresh (matchday) → Run workflow`

- **Inputs:** `n_simulations` (default 10000), `dry_run` (default false — when true, everything runs but nothing is committed or pushed).
- **Required repository secret:** `FOOTBALL_DATA_ORG_KEY` (the live provider credential). Optional: `API_FOOTBALL_KEY`. Secrets are passed as environment variables only — never written to files, never printed.
- **Stages:** checkout → install → `refresh-portfolio` → eligibility gate (reads the manifest) → commit-safety gate (allowlist + secret scan + private-path scan + unexpected-file rejection) → commit/push of allowlisted files only → manifest uploaded as a workflow artifact.
- **The workflow refuses publication when:** `eligible_for_publication` is false, unexpected files changed, any staged file hits the secret/path scan, or there is nothing allowlisted to commit. The run log states the reason; the previous public data and git history are untouched.
- `validate.yml` runs offline validation (backend suite + website lint/build + pytest) on every PR and push to `main`; it needs no secrets and never calls live APIs.

## Emergency fallback behavior

- **Provider unavailable / rate-limited:** the provider layer preserves last-good normalized data, honors `Retry-After` (capped), and `live_provider_freshness.json` discloses `data_source_mode` (`cached_normalized` / `saved_snapshot`) and `rate_limited`. The quality gate — not the frontend — decides whether the output may still be called a true live forecast.
- **Live forecast validation fails:** refresh reports `live_forecast_status != success`, eligibility is false, nothing is published.
- **Public export validation fails:** staged exports are discarded; `public_data/` keeps the previous known-good dataset; manifest shows `public_export_publication: rejected` with the failed checks.
- **Unexpected files changed:** `check-commit-safety` (and the Actions gate) stops and lists them — investigate before committing anything.
- **Git push fails (e.g. remote diverged):** the commit exists locally / in the runner only; `git pull --rebase` and re-push manually. No data is lost.

## Secret configuration summary

- Local: `.env` (never committed; verified by scans).
- GitHub Actions: encrypted repository secrets `FOOTBALL_DATA_ORG_KEY` (+ optional `API_FOOTBALL_KEY`).
- Vercel: **no provider secret needed** — the website statically renders committed `public_data/`. Optional display vars: `NEXT_PUBLIC_DASHBOARD_URL`, `NEXT_PUBLIC_GITHUB_URL`.
- Streamlit Cloud: **no secrets needed** — the dashboard reads committed saved outputs and never calls the provider.
