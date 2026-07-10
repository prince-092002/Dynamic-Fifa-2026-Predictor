# Phase 5F Live Knockout Feature + Model Prediction Regeneration Handoff

Saved: 2026-07-09  
Scope: generate model features and XGBoost predictions for resolved live knockout matchups so the live finalist/champion forecast is driven by the trained model wherever possible, instead of falling back to Elo for almost every remaining match. Elo fallback is kept as backup only. No secrets are included.

## Why This Phase Existed

The Phase 5E audit found that `fixture_2026_match_predictions.csv` only has predictions for the pre-tournament fixture template. Once real knockout pairings are known (e.g. France vs Morocco in the quarterfinal), no exact-match prediction exists for them, so the live simulator fell through to Elo for ~99.6% of simulated remaining matches. This phase closes that gap.

## What Changed

- Added:
  - `src/live_state/live_matchup_features.py` — identifies unplayed knockout matches with both teams known (`identify_remaining_live_knockout_matches`) and builds model features for them by reusing the Phase 3 feature functions (`build_live_knockout_features`).
  - `src/live_state/live_matchup_predictor.py` — runs the selected model on those features (`predict_live_knockout_matchups`), exposes a team-pair probability lookup for the simulator (`load_live_knockout_prediction_lookup`), and bundles all three steps (`run_live_knockout_prediction_flow`).
  - `src/live_state/live_prediction_reports.py` — writes `live_knockout_prediction_report.md` and an 11-check `live_knockout_prediction_validation.md`.
- Updated:
  - `src/simulation/bracket_mapping.py` — `get_dynamic_match_probabilities` takes an optional `live_probability_lookup` checked before the existing prediction-file lookup; returns `live_model_exact` / `live_model_reversed` sources.
  - `src/live_state/finalist_simulator.py` — threads the live lookup through group/knockout simulation paths; snapshots the previous probability-source counts to `live_probability_source_counts_previous.json` before each run so before/after fallback comparisons are possible.
  - `src/live_state/live_pipeline.py` — `run_live_forecast_pipeline` now runs the matchup-prediction step before simulating (new `skip_live_matchup_predictions` param / `--skip-live-matchup-predictions` CLI flag); failures in that step never block the forecast, they just leave Elo fallback in place.
  - `src/live_state/live_reports.py` — `finalist_prediction_summary.md` now states the selected provider and live-model vs Elo usage percentages; `end_of_matchday_update_summary.md` states live matchup prediction status and count.
  - `src/live_state/live_validation.py` — reads current phase from the quality gate JSON instead of the stale `current_tournament_state.csv` detector (bug fix carried over from the Phase 5E audit).
  - `main.py` — new commands and the `--skip-live-matchup-predictions` flag on `run-live-forecast`.

## New Commands

```bash
python main.py identify-live-knockout-matchups
python main.py build-live-knockout-features
python main.py predict-live-knockout
python main.py live-knockout-prediction-summary
python main.py run-live-forecast --n-simulations 10000 --skip-live-matchup-predictions
```

## Probability Source Ladder (Updated)

1. `completed_result` — locked, never re-simulated
2. `live_model_exact` / `live_model_reversed` — XGBoost prediction for the actual resolved knockout matchup
3. `model_exact` / `model_reversed` — prediction from the pre-tournament fixture file, if it happens to match
4. `elo_fallback` — Elo rating expected score
5. `neutral_fallback` — flat 35/30/35 when nothing else is available

## Verification Run

Commands run:

```bash
python -m compileall src main.py scripts
python main.py identify-live-knockout-matchups
python main.py build-live-knockout-features
python main.py predict-live-knockout
python main.py live-knockout-prediction-summary
python main.py run-live-forecast --n-simulations 1000
python main.py validate-live-forecast
python main.py run-live-forecast --n-simulations 10000
python main.py validate-live-forecast
python main.py live-forecast-summary
python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain
```

Results:

- Compile: pass.
- Known remaining knockout matchups detected: `4` (France vs Morocco, Spain vs Belgium, Norway vs England, Argentina vs Switzerland — all Quarterfinal).
- Knockout matches correctly skipped: `24` completed, `3` TBD (semifinals + final).
- Live knockout features: `4/4` complete, `0` missing feature values.
- Live knockout predictions: `4/4` predicted by `xgboost`, `0` failed.
  - France vs Morocco: advance `0.6997` / `0.3003`, pick France
  - Spain vs Belgium: advance `0.7258` / `0.2742`, pick Spain
  - Norway vs England: advance `0.3619` / `0.6381`, pick England
  - Argentina vs Switzerland: advance `0.7655` / `0.2345`, pick Argentina
- `live-knockout-prediction-summary` validation: pass (10/11 checks pass; 1 warn on first run because no previous baseline existed yet — resolved on the next run).
- 1,000-run live forecast: `success`. Probability source counts: `live_model_exact 4000`, `elo_fallback 2956`, `model_reversed 44`. Elo/neutral fallback share dropped `99.63% -> 42.23%` versus the pre-Phase-5F baseline.
- `validate-live-forecast`: pass.
- 10,000-run live forecast: `success`. Probability source counts: `live_model_exact 40000`, `elo_fallback 29643`, `model_reversed 357`. Fallback share `42.35%` (structural floor at the quarterfinal stage — semifinal/final matchups inside each simulated branch cannot be predicted ahead of time because their real participants are not yet known).
- Finalist pair probabilities sum: `1.0000`. Champion probabilities sum: `1.0000`. No eliminated team appears as finalist or champion.
- 10,000-run top champion probabilities: Argentina `0.2577`, Spain `0.2120`, France `0.2100`, England `0.1565`, Morocco `0.0554`, Belgium `0.0489`, Switzerland `0.0350`, Norway `0.0245`.
- 10,000-run top finalist pair: Argentina vs France, `0.1868`.
- Matchday update smoke test completed:
  - live forecast: `success`
  - live matchup predictions: `success (4 matchups predicted by the model)`
  - broader refresh validation: `failed` due to the same three pre-existing data validation checks noted in the Phase 5E handoff (unrelated to live forecasting).
- Secret scan: `0` output/report/source files contain any `.env` value. `.env` remains untracked and gitignored.

## Outputs Created

```text
outputs/live_state/remaining_known_knockout_matchups.csv
outputs/live_state/live_knockout_match_features.csv
outputs/live_state/live_knockout_match_predictions.csv
outputs/live_state/live_probability_source_counts_previous.json
outputs/reports/live_state/live_knockout_prediction_report.md
outputs/reports/live_state/live_knockout_prediction_validation.md
```

## Bug Found and Fixed

`data/processed/matches_master.csv` contains unplayed fixture placeholder rows with `NaN` goals (from the Kaggle 2026 feed, including the quarterfinals themselves). These were being included in the live knockout feature history, which corrupted rest-day/schedule features (a team's own upcoming fixture was leaking into its "days since last match" calculation) and blocked real completed live results from being appended because they looked like duplicates of the placeholder row's date. Fixed in `live_matchup_features._build_combined_history` by dropping rows with missing goals before deduplication against live results. Rebuilt features afterward show correct rest days (3-6 days for all four QF teams) and correct recent-form history including Round of 16 results.

## Important Notes

- Elo fallback is retained as backup, exactly as before, and is never relabeled as a model prediction; `probability_source` in every output distinguishes `live_model_exact`, `live_model_reversed`, `model_exact`, `model_reversed`, `elo_fallback`, and `neutral_fallback`.
- The live feature build reuses the same Phase 3 feature functions used for training, so live knockout features stay consistent with what the model was trained on — no new feature logic or retraining was introduced.
- The live knockout feature build costs roughly 3-5 minutes per invocation because it replays `calculate_team_match_history` over the full ~50k-row match history (same cost the original `build-features` phase pays). This runs automatically before every `run-live-forecast` and every matchday update unless `--skip-live-matchup-predictions` is passed. Caching the team history and only appending new completed matches is a reasonable future optimization, not done in this phase.
- Semifinal and final matchups remain on Elo fallback inside each simulated branch until their real participants are known in the live bracket — this is expected and will resolve automatically once football-data.org populates those bracket rows after the quarterfinals are played. No manual action is needed; the next `run-live-forecast` or matchday update will pick up newly resolved matchups.
- No dashboard was built.
