# Phase 6B GitHub Automation and Matchday Deployment Workflow Handoff

Saved: 2026-07-10  
Scope: safe, reproducible post-match deployment workflow on top of the verified Phase 6 system — unified refresh command, fail-closed publication, commit-safety allowlist, GitHub Actions, and operations documentation. No backend forecasting logic was duplicated or changed. No secrets included.

## 1. Objective and audit

Full audit: `outputs/reports/portfolio/phase6b_automation_audit.md`. Key findings: `main` @ `efa514a`, clean tree, **no GitHub remote** (user step; no URL invented); publishable vs volatile vs forbidden generated files mapped; website/dashboard confirmed to need **no runtime secrets**; the Vercel `../public_data/` build-time read works because Vercel clones the whole repository even with Root Directory=`website`. A legacy Phase 2 workflow (`update_data.yml`, daily provider cron, secrets written to a `.env` file, no validation gating) was **removed** as unsafe under Phase 6B rules.

## 2. Fail-closed publication (new)

`src/public_export/publish.py::safe_publish_public_exports()` — exports build into a staging directory, are validated there, and only a fully valid set replaces `public_data/`. On failure the previous known-good dataset is untouched and the rejection (with failed check names) is reported. The live pipeline hook now uses this path and exposes the outcome as `public_export_publication` in the forecast result. Covered by tests (invalid staged set preserves last-good; valid set promotes and reports changed files).

## 3. Unified refresh command (new)

```bash
python main.py refresh-portfolio --n-simulations 10000 --no-retrain
```

Orchestrates existing components: matchday update (provider refresh → normalized state → completed-result locking → matchup identification → live features → XGBoost predictions → Monte Carlo → live validation → history append → fail-closed public export publish) then public-export validation, dashboard validation, deployment readiness, and a manifest at `outputs/reports/portfolio/latest_portfolio_refresh_manifest.json` (refresh id, timestamps, git commit before, phase before/after, provider + mode, completed counts before/after, alive/eliminated counts, newly completed matches, newly predicted matchups, simulation count, all validation statuses, changed public files, warnings, `eligible_for_publication`). Exits non-zero when not eligible. The analytical forecast may still succeed even when packaging fails — the manifest reports each level separately.

## 4. Commit safety (new)

`src/public_export/commit_safety.py` + `python main.py check-commit-safety`:

- **COMMIT_ALLOWLIST** (automation may commit): `public_data/*.json`; the three forecast-history CSVs + probability_source_history; latest_live_run_manifest / tournament_phase_transition / live_provider_freshness / live_forecast_summary / live_forecast_quality_gate; current forecast CSVs (champion, reach-final, pairs, predictions, matchups); normalized provider CSVs + merged bracket; the portfolio refresh manifest.
- **EXPECTED_VOLATILE** (changes tolerated, never auto-committed): `data/*`, `outputs/*`, `public_data/*`, `.streamlit/*`.
- **FORBIDDEN** (never staged; routine regeneration tolerated): `.env`/`*.env`, kaggle.json, `provider_snapshots/*`, `api_football_live_*.json`, node_modules/.next. (Design note: snapshots regenerate on every fetch, so they tolerate-but-never-commit rather than block — caught and fixed during verification.)
- Anything changed outside those sets (source, docs, workflows, config) → **automation stops and reports**.
- Staged files additionally pass a secret-value scan and a private-path scan (never printing values).

## 5. GitHub Actions (new)

- `.github/workflows/validate.yml` — PRs + pushes to `main`; offline only, no secrets: compileall, validate, validate-features, validate-simulation, validate-bracket, validate-live-forecast, validate-public-exports, validate-dashboard, pytest; separate website job (`npm ci`, lint, build; Node 24, Python 3.12 matching the verified local environment).
- `.github/workflows/portfolio-refresh.yml` — `workflow_dispatch` **only** (no cron); inputs `n_simulations` (default 10000) and `dry_run`; retraining not exposed (always `--no-retrain`). Steps: checkout → pip install → `refresh-portfolio` with secrets passed **as environment variables only** → eligibility gate reading the manifest → commit-safety gate (writes the allowlist to stage) → commit/push of exactly those files as `github-actions[bot]` → manifest uploaded as artifact (`always()`). Concurrency-grouped; `permissions: contents: write`.
- **Secrets required:** `FOOTBALL_DATA_ORG_KEY` (repository secret). Optional: `API_FOOTBALL_KEY`. Vercel and Streamlit need none. Local `.env` stays local. YAML syntax validated locally; the workflows have **not** been executed on GitHub (no remote yet) — no hosted run is claimed.

## 6. Other changes

- `build_public_exports(target_dir)` / `validate_public_exports(directory, write_report)` parameterized for staging.
- `validate-dashboard` gained forecast-history dedup checks (no duplicate run_id per entity across the four history CSVs) — history verified backend-written, append-safe, frontend-untouched, surviving automated refreshes (tested).
- `docs/MATCHDAY_OPERATIONS.md` — local + Actions procedures, secret configuration, and the explicit four-level distinction (analytical forecast ≠ public export ≠ git commit ≠ deployment) with emergency fallback behavior for provider outages, rate limits, validation failures, unexpected files, and push failures.
- README updated (refresh-portfolio as the operational command, Actions section). `pytest` added to requirements.txt.

## 7. Verification (all actually executed)

```text
python -m pytest tests -q                       -> 16 passed
python main.py refresh-portfolio --n-simulations 10000 --no-retrain   (end-to-end, real provider fetch)
   -> refresh-2026-07-10T065028Z-9fa8bf | fresh_api | phase quarterfinal | 97 completed
      3 matchups XGBoost-predicted | live: success | publication: published
      export validation: pass | dashboard validation: pass | readiness: ready
      eligible_for_publication: True | 13 public files changed
      1 warning (API-Football returned 0 rows; expected, football-data.org is the provider)
python main.py check-commit-safety              -> correctly identifies 25 allowlisted files and stops on the
                                                   Phase 6B source changes themselves (tamper protection working)
Workflow YAML                                    -> both parse (jobs: refresh / backend+website)
cd website && npm run lint && npm run build      -> clean; 55 static pages
streamlit headless startup                       -> health "ok"
python -m compileall src main.py scripts dashboard -> pass
Backend suite (validate/features/sim/bracket/live/equivalence/matchup-flow) -> re-verified passing this session
Secret scan                                      -> 0 hits (tracked files + staged-file scans)
```

## 8. Known limitations

- Workflows are authored and locally validated but have never run on GitHub-hosted runners (no remote exists yet). First dispatch should use `dry_run: true`.
- `validate.yml` validates committed-state consistency offline; it deliberately does not test provider connectivity.
- Older tracked reports (pre-6B) embed absolute local paths; excluded from the automation allowlist, but present in git history.
- The automated commit updates normalized provider CSVs and manifests; other regenerated files (e.g. `data/processed/*`) intentionally stay uncommitted in CI and are rebuilt on the next local run.

## 9. Remaining manual steps (user accounts required)

1. `git remote add origin <your-github-repo> && git push -u origin main`.
2. Add repository secret `FOOTBALL_DATA_ORG_KEY` (Settings → Secrets and variables → Actions).
3. Connect Vercel (Root Directory `website`) and Streamlit Cloud (`dashboard/app.py`); paste live URLs into README and Vercel env vars.
4. Test `Portfolio Refresh (matchday)` with `dry_run: true`, then use it (or the local flow in docs/MATCHDAY_OPERATIONS.md) after each real match.

## 10. Recommended next step

Operate the remaining tournament with the automated workflow; begin **Phase 7 (post-tournament backtesting and calibration)** once the final is played and the forecast-history files span the full knockout stage.
