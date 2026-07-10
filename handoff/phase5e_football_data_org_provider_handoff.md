# Phase 5E football-data.org Provider Handoff

Saved: 2026-07-08  
Scope: add football-data.org as an alternate FIFA World Cup live provider while preserving API-Football, fallback mode, and the true-live quality gate. No secrets are included.

## What Changed

- Added `.env.example` keys:
  - `FOOTBALL_DATA_ORG_KEY=`
  - `FOOTBALL_DATA_ORG_COMPETITION_ID=2000`
  - `FOOTBALL_DATA_ORG_COMPETITION_CODE=WC`
  - `FOOTBALL_DATA_ORG_SEASON=2026`
- Added config reads in `src/config.py`.
- Added provider package:
  - `src/live_state/providers/__init__.py`
  - `src/live_state/providers/football_data_org_provider.py`
- Added provider diagnostics and selection:
  - `src/live_state/provider_diagnostics.py`
  - `src/live_state/provider_registry.py`
- Updated:
  - `src/live_state/live_pipeline.py`
  - `src/live_state/live_quality_gate.py`
  - `src/live_state/bracket_state.py`
  - `src/live_state/standings_builder.py`
  - `src/live_state/state_builder.py`
  - `src/live_state/finalist_simulator.py`
  - `src/live_state/live_source_config.py`
  - `src/live_state/current_phase_detector.py`
  - `main.py`
  - `README.md`

## New Commands

```bash
python main.py diagnose-football-data-org
python main.py fetch-football-data-org
python main.py normalize-football-data-org
python main.py diagnose-live-providers
python main.py select-live-provider
python main.py live-source-summary
python main.py live-quality-gate
```

## Verification Run

Commands run:

```bash
python -m compileall src main.py scripts
python main.py diagnose-football-data-org
python main.py fetch-football-data-org
python main.py normalize-football-data-org
python main.py diagnose-live-providers
python main.py select-live-provider
python main.py live-source-summary
python main.py live-quality-gate
python main.py run-live-forecast --n-simulations 1000
python main.py validate-live-forecast
python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain
```

Results:

- Compile: pass.
- football-data.org provider status: `available_true_live`.
- football-data.org token present: `true`, hidden in logs/reports.
- football-data.org fixture rows: `104`.
- football-data.org completed rows: `96`.
- football-data.org team rows: `48`.
- football-data.org standings rows: `144`.
- football-data.org bracket rows: `32`.
- API-Football provider status: `no_2026_rows`.
- Selected live provider: `football_data_org`.
- Quality gate:
  - `forecast_mode`: `true_live_forecast`
  - `source_quality_score`: `100`
  - `current_phase`: `quarterfinal`
  - completed result count: `96`
  - fallback usage: `9.68%`
  - finalist forecast allowed by default: `true`
- `run-live-forecast --n-simulations 1000` completed successfully.
- Top finalist pair: Argentina vs France, `0.1600`.
- Top champion: Argentina, `0.2090`.
- `validate-live-forecast` passed.
- Matchday update smoke test completed:
  - live forecast: `success`
  - broader refresh validation: `failed` due existing data validation checks.

## Outputs Created

```text
outputs/live_state/provider_snapshots/football_data_org/
outputs/live_state/football_data_org_fixtures_normalized.csv
outputs/live_state/football_data_org_teams_normalized.csv
outputs/live_state/football_data_org_standings_normalized.csv
outputs/live_state/football_data_org_bracket_normalized.csv
outputs/reports/live_state/providers/football_data_org_provider_report.md
outputs/reports/live_state/providers/provider_comparison.csv
outputs/reports/live_state/providers/provider_selection_report.md
```

The normalized football-data.org CSVs contain real 2026 rows from the verified provider run.

## Important Notes

- No football-data.org token was printed or saved.
- Add or rotate the token locally as:

```text
FOOTBALL_DATA_ORG_KEY=your_token_here
```

- To re-check the provider, rerun:

```bash
python main.py diagnose-football-data-org
python main.py diagnose-live-providers
python main.py select-live-provider
python main.py live-quality-gate
```

- football-data.org currently exposes usable FIFA World Cup 2026 rows for this token, but repeated diagnostics may hit rate limits.
- The provider preserves the last good normalized files and `normalize-football-data-org` can rebuild normalized outputs from saved sanitized snapshots when the latest API call is rate-limited.
- The quality gate decides whether forecasts are true live, partially live, fallback, or insufficient on each run.
- No dashboard was built.
