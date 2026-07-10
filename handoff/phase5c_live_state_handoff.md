# Phase 5C Live State Handoff

Saved: 2026-07-07  
Scope: live tournament state, finalist-pair forecasting, champion forecasting, and matchday update integration. No secrets are included.

## What Changed

- Added `src/live_state/` package:
  - `live_config.py`
  - `api_football_live.py`
  - `fifa_live.py`
  - `state_builder.py`
  - `standings_builder.py`
  - `bracket_state.py`
  - `finalist_simulator.py`
  - `finalist_aggregation.py`
  - `live_validation.py`
  - `live_reports.py`
  - `live_pipeline.py`
- Added CLI commands:
  - `python main.py fetch-live-state`
  - `python main.py build-live-state`
  - `python main.py run-live-forecast --n-simulations 10000`
  - `python main.py validate-live-forecast`
  - `python main.py live-forecast-summary`
- Updated matchday automation:
  - `python main.py update --mode matchday --run-live-forecast --n-simulations 10000 --no-retrain`
- Updated `README.md` with Phase 5C usage and limitations.

## Latest Verified Commands

```bash
python -m compileall src main.py scripts
python main.py fetch-live-state
python main.py build-live-state
python main.py run-live-forecast --n-simulations 1000
python main.py validate-live-forecast
python main.py live-forecast-summary
python main.py run-live-forecast --n-simulations 10000
python main.py validate-live-forecast
python main.py live-forecast-summary
python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain
```

The first update integration attempt was blocked by sandbox network permissions. It was rerun with network approval and completed the live forecast path.

## Verified 10,000-Run Live Forecast

- Current phase: `pre_group_stage`
- Finalist prediction active: `true`
- Finalist pair probability sum: `1.0`
- Champion probability sum: `1.0`
- Fallback bracket usage: `100%`
- Top finalist pair: `Argentina vs France` at `0.0317`
- Top champion: `Spain` at `0.1286`

Top reach-final teams from the 10,000-run forecast:

| Team | Reach-final probability |
|---|---:|
| Spain | 0.2031 |
| France | 0.1960 |
| Argentina | 0.1897 |
| England | 0.1332 |
| Brazil | 0.1324 |

Top champion probabilities from the 10,000-run forecast:

| Team | Champion probability |
|---|---:|
| Spain | 0.1286 |
| Argentina | 0.1213 |
| France | 0.1177 |
| England | 0.0774 |
| Brazil | 0.0705 |

## Matchday Update Integration

Command tested:

```bash
python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain
```

Result:

- Update source: `existing_processed_csv`
- New completed matches: `0`
- Existing processed-data validation status: `failed`
- Live forecast status: `success`
- End-of-matchday report written:
  - `outputs/reports/live_state/end_of_matchday_update_summary.md`

The validation failure is from the existing data refresh validation, not from the live forecast. The live forecast validation passed afterward.

Because the update integration test ran after the 10,000-run verification, the current `outputs/live_state/` forecast CSVs reflect the 1,000-simulation update test. Rerun `python main.py run-live-forecast --n-simulations 10000` whenever the saved output files should be refreshed back to 10,000 simulations.

## Key Outputs

```text
outputs/live_state/current_tournament_state.csv
outputs/live_state/current_tournament_state.json
outputs/live_state/current_group_standings.csv
outputs/live_state/current_third_place_table.csv
outputs/live_state/current_knockout_bracket.csv
outputs/live_state/merged_bracket_state.csv
outputs/live_state/remaining_match_probabilities.csv
outputs/live_state/live_finalist_simulation_results.csv
outputs/live_state/live_simulated_match_results_sample.csv
outputs/live_state/finalist_pair_probabilities.csv
outputs/live_state/team_reach_final_probabilities.csv
outputs/live_state/live_champion_probabilities.csv
outputs/live_state/live_forecast_summary.json
outputs/reports/live_state/live_validation_report.md
outputs/reports/live_state/finalist_prediction_summary.md
outputs/reports/live_state/live_bracket_source_report.md
```

## Important Caveats

- The current live API did not provide standings rows, so standings are computed from completed matches when possible.
- Current phase is `pre_group_stage` because there are no completed FIFA 2026 tournament results in the local processed data.
- Current bracket usage is `100%` fallback because no trustworthy live/API or official knockout pairings are available yet.
- Fallback mapping is not official FIFA mapping.
- Completed results are locked when present and are not overwritten by simulation.
- No dashboard was built.
