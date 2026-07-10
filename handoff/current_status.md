# Current Project Status

Project: Dynamic FIFA 2026 Tournament Outcome Predictor  
Saved: 2026-07-10 (post Phase 6B)  
Scope: current state snapshot for next session. No secrets are included.

## Completed Phases

- Phase 1: Data foundation
- Phase 2: Automatic update workflow
- Phase 2.5: Real data loading
- Phase 3: Data quality cleanup and feature engineering
- Phase 4: Modeling pipeline
- Phase 5: Monte Carlo tournament simulation
- Phase 5B: Fallback bracket mapping and full champion simulation
- Phase 5C: Live tournament state and finalist prediction
- Phase 5D: True-live source verification and finalist forecast quality gate
- Phase 5E: football-data.org live provider integration
- Phase 5F: Live knockout feature + model prediction regeneration
- Phase 5G: Live pipeline reliability, validation cleanup, feature performance, matchday automation hardening
- Phase 6: Public website (Next.js/Vercel-ready), Streamlit dashboard, public data exports, GitHub repository readiness
- Phase 6B: GitHub automation and matchday deployment workflow

## Phase 6B verified state (2026-07-10)

- One-command operational refresh: `python main.py refresh-portfolio --n-simulations 10000 --no-retrain` — verified end-to-end against the live provider: eligible_for_publication True, publication published, 13 public files changed, all validations pass.
- Fail-closed publication: staged exports validated before promotion; invalid exports can never replace the last known-good `public_data/` (tested).
- Commit safety: strict allowlist + secret/path scans + unexpected-file stop (`python main.py check-commit-safety`); provider snapshots and credentials can never be auto-committed.
- GitHub Actions: `validate.yml` (offline CI, secret-free: backend suite + pytest + website lint/build) and `portfolio-refresh.yml` (manual dispatch only, gated commit of allowlisted artifacts, `FOOTBALL_DATA_ORG_KEY` secret, dry-run supported). Legacy unsafe daily-cron workflow removed. Workflows locally YAML-validated; not yet executed on GitHub (no remote configured).
- Forecast-history dedup validation added to `validate-dashboard`; tests: 16/16 pass (`python -m pytest tests -q`).
- Docs: `docs/MATCHDAY_OPERATIONS.md` (local + Actions procedures, four-level success distinction, emergency fallbacks), `outputs/reports/portfolio/phase6b_automation_audit.md`.
- Remaining manual steps: add GitHub remote + push, set `FOOTBALL_DATA_ORG_KEY` repo secret, connect Vercel (root `website`) and Streamlit Cloud (`dashboard/app.py`), first Actions run with dry_run.
- See `handoff/phase6b_automation_handoff.md`.

## Phase 6 verified state (2026-07-10)

- Git repository initialized (`main`, initial commit `3e240d4`); secret scan over all 421 tracked files: 0 hits; `.env`/node_modules/backups ignored.
- Public export layer: `python main.py build-public-exports` writes 13 JSON contracts to `public_data/` (documented in `PUBLIC_DATA_CONTRACT.md`); rebuilt automatically at the end of every live forecast run.
- New validations, all passing: `validate-public-exports` (31 checks), `validate-dashboard` (6 checks), `validate-deployment-readiness` (8/8 ready).
- Forecast history persistence added (champion/finalist/pair CSVs, append-safe, run_id-deduplicated, backend-written).
- Streamlit dashboard: `streamlit run dashboard/app.py` — overview + 8 pages, startup health verified, renders from saved outputs with no API access.
- Next.js website: `website/` — lint clean, production build passes (Next 15.5.20, 55 static pages incl. all 48 team pages), fully static from `public_data/`.
- Team lifecycle (alive/eliminated/champion/runner-up) derived from real bracket state; team statistics from completed real fixtures only.
- Current export values: phase quarterfinal, 97 completed, 7 alive / 41 eliminated, 3 unresolved matchups (all live-XGBoost predicted), 10,000 sims, top champion France 29.49%, top final Argentina vs France 26.07%, both validations pass.
- Remaining manual steps: push to GitHub, connect Vercel (root dir `website`) and Streamlit Cloud (`dashboard/app.py`), paste live URLs into README.
- See `handoff/phase6_public_website_dashboard_deployment_handoff.md`.

## Latest Verified State

Feature engineering:

- `data/features/final/match_training_dataset.csv` exists with real rows.
- `data/features/final/fixture_2026_features.csv` exists with real rows.
- `python main.py validate-features` passed.
- Leakage checks passed.

Modeling:

- Baselines, Logistic Regression, and XGBoost were trained.
- Selected model: `xgboost`.
- Selected model artifact:
  - `outputs/models/selected_model.joblib`
- Fixture predictions:
  - `outputs/predictions/fixture_2026_match_predictions.csv`
- Latest prediction file state:
  - 104 total fixture rows
  - 51 predicted fixtures
  - 53 not predictable rows

Simulation:

- `python main.py run-simulation --mode partial --n-simulations 1000` completed.
- `python main.py run-simulation --mode full-bracket --n-simulations 10000` completed.
- `python main.py validate-simulation` passed.
- `python main.py validate-bracket` passed.
- Main simulation outputs:
  - `outputs/simulations/team_advancement_probabilities.csv`
  - `outputs/simulations/champion_probabilities.csv`
  - `outputs/simulations/stage_probability_summary.csv`
  - `outputs/simulations/simulated_match_results_sample.csv`
  - `outputs/simulations/bracket_completion_summary.csv`
  - `outputs/simulations/probability_source_summary.csv`

Phase 5B latest full-bracket result:

- Full bracket completion rate: `1.0000`
- Completed simulations: `10000 / 10000`
- Champion probability sum: `1.0`
- Top champion probabilities:
  - Spain: `0.1264`
  - Argentina: `0.1188`
  - France: `0.1110`
  - England: `0.0832`
  - Brazil: `0.0708`
- Probability source usage:
  - model exact: `1118`
  - model reversed: `685`
  - Elo fallback: `308197`
  - neutral fallback: `0`

Phase 5C/5E/5F/5G current live forecast:

- **The real tournament moved during Phase 5G: France defeated Morocco 2-0 in the first quarterfinal.** The pipeline handled the transition live: the result locked automatically, Morocco left the surviving set, and the remaining 3 matchups were re-predicted.
- `python main.py run-live-forecast --n-simulations 10000` completed successfully; `validate-live-forecast` passed (19 checks).
- Current provider: `football_data_org` (`data_source_mode: fresh_api`, age 0 min).
- Current forecast mode: `true_live_forecast`.
- Current phase: `quarterfinal`.
- Source quality score: `100`.
- Live fixture rows: `104`.
- Completed fixtures: `97`.
- Known unresolved knockout matchups: `3` (Spain-Belgium, Norway-England, Argentina-Switzerland), all predicted by XGBoost.
- Fallback bracket usage: `9.68%`.
- Finalist prediction active: `true`.
- Verified 10,000-run finalist pair: Argentina vs France, `0.2607`.
- Verified 10,000-run champion: France, `0.2949`.
- Probability source usage (1,000-run manifest): `completed_result 1000`, `live_model_exact 3000`, `elo_fallback 2945`, `model_reversed 55` (model-driven ~43.6%, fallback ~42.1%).
- Seed-42 runs are byte-identical (reproducibility verified across two full pipeline runs).
- Matchday update integration ran with:
  - `python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain`
  - Live forecast status: `success`
  - Live matchup predictions: `success (3 matchups predicted by the model)`
  - **Broader data refresh validation status: `passed`** (the three long-standing failures were root-caused and fixed in Phase 5G; see `outputs/reports/data_validation_failure_audit.md`)

Phase 5G reliability additions:

- `python main.py validate` now reports 22 pass / 3 warn / 0 fail (expected conditions are warns, genuine defects still fail; a new fail-capable check guards the deduplicated feature-clean file).
- Live knockout feature build: `245s -> 1.7s` (root cause: per-call team-name-map reloads; fix equivalence-proven, 112/112 feature values exactly identical — `python main.py validate-live-feature-equivalence`).
- Live feature history now uses the deduplicated `matches_master_feature_clean.csv` (training lineage) instead of the raw master.
- Sandboxed integration check `python main.py validate-live-matchup-flow` proves newly resolved matchups flow to XGBoost predictions and `live_model_exact` in the simulator (8/8 checks).
- New audit artifacts per run: `tournament_phase_transition.json`, `live_provider_freshness.json`, `probability_source_history.csv`, `probability_source_progression.md`, `latest_live_run_manifest.json`.
- `validate-live-forecast` expanded from 9 to 19 integrity checks (eliminated-team, source-label, completed-lock, gate-agreement, freshness-disclosure checks all fail-capable).
- Provider requests honor `Retry-After` (capped); last-good normalized data preserved on failures; cache/snapshot use disclosed honestly.

Phase 5D true-live gate:

- `python main.py diagnose-live-api` completed with network approval.
- API-Football key is present but hidden.
- API-Football season 2026 endpoints returned no usable rows because the current API plan does not expose 2026 season data.
- `python main.py live-quality-gate` completed.
- Current gate:
  - `forecast_mode`: `true_live_forecast`
  - `source_quality_score`: `100`
  - `current_phase`: `quarterfinal`
  - completed result count: `96`
  - fallback usage: `9.68%`
  - finalist forecast allowed by default: `true`
- Existing data refresh validation still reports `failed` due three pre-existing data validation checks; live forecast validation passes.

Phase 5E football-data.org provider:

- Added football-data.org env/example keys, provider class, diagnostics, provider registry, provider selection, quality gate scoring, and CLI commands.
- `python main.py diagnose-football-data-org` completed.
- Current football-data.org provider status: `available_true_live`.
- Current football-data.org fixture rows: `104`.
- Current football-data.org completed rows: `96`.
- Current football-data.org team rows: `48`.
- Current football-data.org standings rows: `144`.
- Current football-data.org bracket rows: `32`.
- `python main.py diagnose-live-providers` completed with network approval.
- Provider comparison:
  - API-Football: `no_2026_rows`, score `0`
  - football-data.org: `available_true_live`, score `105`
- Selected provider: `football_data_org`.
- The provider preserves the last good normalized CSVs and can rebuild normalized outputs from saved sanitized snapshots if a later request is rate-limited.

Phase 5F live knockout predictions:

- Added `identify-live-knockout-matchups`, `build-live-knockout-features`, `predict-live-knockout`, and `live-knockout-prediction-summary` commands.
- Known remaining knockout matchups detected: `4` (all Quarterfinal, both teams known from the live bracket).
- Live knockout features: `4/4` complete, `0` missing feature values.
- Live knockout predictions: `4/4` predicted by `xgboost`, `0` failed.
- `live-knockout-prediction-summary` validation: pass.
- The live simulator now prefers `live_model_exact`/`live_model_reversed` probabilities before falling through to the pre-tournament prediction file or Elo fallback.
- Semifinal/final matchups inside each simulated branch still use Elo fallback until their real participants are known in the live bracket; this resolves automatically as later rounds are played, no manual action needed.
- See `handoff/phase5f_live_knockout_predictions_handoff.md` for full details.

## Important Limitations

- Full champion simulation now works with explicit fallback bracket mapping.
- The fallback bracket and third-place placement mapping are not official FIFA rules and must be replaced when official mapping is available.
- TBD/playoff placeholder fixtures are preserved and not treated as real teams.
- Exact model probabilities now exist for resolved live knockout matchups (Phase 5F); matchups whose participants are not yet known (future semifinals/final) still use Elo fallback until the real bracket resolves them.
- Live API standings may be unavailable; the live phase computes standings from completed matches when needed.
- Current live forecast uses football-data.org live fixtures/results/standings and only keeps fallback for bracket rows that football-data.org has not populated yet.
- Phase 5D prevents fallback-only output from being mislabeled as a true live forecast.
- API-Football free/current plan does not expose season 2026 data for the configured/default league ID.
- football-data.org returned real 2026 rows in the latest verification, but repeated diagnostics may hit rate limits. Reports should state when cached normalized data or saved snapshots are used.
- Do not call football-data.org schedule-only data a true live forecast; the quality gate must decide each run.
- FIFA 2026 results are still not fully loaded if `results_2026.csv` remains header-only.
- Team/player stats are not part of the model while their processed files are header-only.
- Predictions and simulations are probabilistic estimates, not guarantees.

## Most Relevant Handoffs

- `handoff/phase3_feature_engineering_handoff.md`
- `handoff/phase4_modeling_handoff.md`
- `handoff/phase5_simulation_handoff.md`
- `handoff/phase5b_bracket_mapping_handoff.md`
- `handoff/phase5c_live_state_handoff.md`
- `handoff/phase5d_true_live_gate_handoff.md`
- `handoff/phase5e_football_data_org_provider_handoff.md`
- `handoff/phase5f_live_knockout_predictions_handoff.md`
- `handoff/phase5g_live_reliability_and_validation_handoff.md`
- `handoff/real_data_loading_handoff.md`

## Useful Commands

```bash
python main.py data-summary
python main.py ready-for-features
python main.py feature-summary
python main.py modeling-summary
python main.py simulation-summary
python main.py bracket-summary
python main.py champion-summary
python main.py live-forecast-summary
python main.py live-source-summary
python main.py diagnose-football-data-org
python main.py diagnose-live-providers
python main.py select-live-provider
```

To refresh current simulation outputs from existing predictions:

```bash
python main.py run-simulation --mode full-bracket --n-simulations 10000
python main.py validate-simulation
python main.py champion-summary
```

To refresh current live finalist forecast:

```bash
python main.py run-live-forecast --n-simulations 10000
python main.py validate-live-forecast
python main.py live-forecast-summary
```

To run true-live verification:

```bash
python main.py diagnose-live-api
python main.py verify-live-sources
python main.py live-quality-gate
python main.py live-source-summary
```

To test football-data.org:

```bash
python main.py diagnose-football-data-org
python main.py fetch-football-data-org
python main.py normalize-football-data-org
python main.py diagnose-live-providers
python main.py select-live-provider
python main.py live-quality-gate
```

To regenerate live knockout model predictions:

```bash
python main.py identify-live-knockout-matchups
python main.py build-live-knockout-features
python main.py predict-live-knockout
python main.py live-knockout-prediction-summary
```

To run Phase 5G reliability checks:

```bash
python main.py validate-live-feature-equivalence
python main.py validate-live-matchup-flow
```

To run fallback forecast explicitly for testing:

```bash
python main.py run-live-forecast --n-simulations 1000 --allow-fallback-forecast
```

## Recommended Next Step

Operate the tournament: run `python main.py update --mode matchday --run-live-forecast --n-simulations 10000 --no-retrain` after each remaining knockout round. Newly resolved matchups are predicted automatically, the phase transition and probability-source progression are recorded per run, and `latest_live_run_manifest.json` documents each run for review. Once the tournament completes, the dashboard phase can begin — the pipeline is now stable, validated, and auditable enough to present.
