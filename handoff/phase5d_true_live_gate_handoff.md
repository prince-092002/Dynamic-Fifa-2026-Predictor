# Phase 5D True-Live Forecast Gate Handoff

Saved: 2026-07-07  
Scope: true-live source diagnostics, live source quality gate, and gated finalist forecast behavior. No secrets are included.

## What Changed

- Added live source verification modules:
  - `src/live_state/live_source_config.py`
  - `src/live_state/current_phase_detector.py`
  - `src/live_state/api_football_diagnostics.py`
  - `src/live_state/source_verification.py`
  - `src/live_state/live_quality_gate.py`
- Updated:
  - `src/live_state/api_football_live.py`
  - `src/live_state/bracket_state.py`
  - `src/live_state/live_pipeline.py`
  - `src/live_state/live_validation.py`
  - `src/live_state/live_reports.py`
  - `src/live_state/standings_builder.py`
  - `src/update/update_runner.py`
  - `main.py`
  - `README.md`

## New CLI Commands

```bash
python main.py diagnose-live-api
python main.py verify-live-sources
python main.py live-quality-gate
python main.py live-source-summary
```

Updated forecast behavior:

```bash
python main.py run-live-forecast --n-simulations 1000
python main.py run-live-forecast --n-simulations 1000 --allow-fallback-forecast
```

Updated matchday behavior:

```bash
python main.py update --mode matchday --run-live-forecast --n-simulations 1000
python main.py update --mode matchday --run-live-forecast --allow-fallback-forecast --n-simulations 1000
```

## Verified Results

Compile:

```bash
python -m compileall src main.py scripts
```

Result: pass.

API-Football diagnostic:

- API key present: yes, hidden.
- League ID used: `1`.
- Fixture rows from API-Football 2026: `0`.
- Completed matches from API-Football 2026: `0`.
- Standings rows from API-Football 2026: `0`.
- API returned plan/data limitation: free plan does not expose season 2026.
- Report:
  - `outputs/reports/live_state/source_verification/api_football_live_diagnostic.md`

Quality gate:

- `forecast_mode`: `fallback_pre_tournament_forecast`
- `public_label`: `Pre-tournament fallback forecast, not based on completed 2026 results`
- `source_quality_score`: `0`
- `current_phase`: `pre_group_stage`
- completed result count: `0`
- fallback usage: `100%`
- finalist prediction allowed by default: `false`
- champion prediction allowed by default: `false`

Default forecast command:

```bash
python main.py run-live-forecast --n-simulations 1000
```

Result:

- Stopped by quality gate.
- Status: `blocked_by_quality_gate`.
- No fallback-only forecast is mislabeled as live.

Explicit fallback command:

```bash
python main.py run-live-forecast --n-simulations 1000 --allow-fallback-forecast
```

Result:

- Forecast ran successfully.
- Forecast mode remained `fallback_pre_tournament_forecast`.
- Public label remained explicit that it is not based on completed 2026 results.
- Top finalist pair from latest 1,000-run fallback output: `France vs Spain`, `0.0310`.
- Top champion from latest 1,000-run fallback output: `Spain`, `0.1530`.

Matchday update integration:

```bash
python main.py update --mode matchday --run-live-forecast --n-simulations 1000
```

Result:

- Live forecast status: `blocked_by_quality_gate`.

```bash
python main.py update --mode matchday --run-live-forecast --allow-fallback-forecast --n-simulations 1000
```

Result:

- Live forecast status: `success`.
- Forecast mode: `fallback_pre_tournament_forecast`.
- Existing data refresh validation status still reports `failed` due three pre-existing validation checks; live forecast validation passed.

## Key Outputs

```text
outputs/live_state/source_snapshots/
outputs/live_state/live_rounds.csv
outputs/live_state/live_knockout_bracket_from_api.csv
outputs/live_state/live_forecast_quality_gate.json
outputs/reports/live_state/source_verification/api_football_live_diagnostic.md
outputs/reports/live_state/source_verification/world_cup_league_id_verification.md
outputs/reports/live_state/source_verification/world_cup_league_candidates.csv
outputs/reports/live_state/source_verification/live_fixture_status_report.md
outputs/reports/live_state/source_verification/live_rounds_report.md
outputs/reports/live_state/source_verification/live_standings_report.md
outputs/reports/live_state/source_verification/current_phase_report.md
outputs/reports/live_state/source_verification/live_bracket_status_report.md
outputs/reports/live_state/source_verification/secondary_source_verification_report.md
outputs/reports/live_state/source_verification/live_forecast_quality_gate.md
outputs/reports/live_state/end_of_matchday_update_summary.md
```

## Important Caveats

- API-Football is reachable with the provided key, but the current plan does not expose 2026 season data.
- There are no completed FIFA 2026 results in local processed data.
- There are no live/API standings rows.
- There are no trustworthy live/API knockout pairings.
- Current forecast files reflect the latest explicitly allowed 1,000-run fallback forecast.
- Fallback bracket mapping is not official.
- No dashboard was built.
