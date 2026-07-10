# Dynamic FIFA 2026 Tournament Outcome Predictor

This project builds a dynamic FIFA World Cup 2026 prediction pipeline: data loading, cleaning, feature engineering, match-outcome modeling, Monte Carlo simulation, and explicit fallback bracket mapping for champion probabilities. It does not build a Streamlit dashboard yet.

## Data Sources

- FIFA Data Centre: official fixtures, results, stages, teams, and venues when parseable.
- API-Football/API-Sports: optional live fixtures, results, teams, standings, and stats with `API_FOOTBALL_KEY`.
- Kaggle international football results: historical international match training data.
- Kaggle FIFA World Cup historical data: World Cup-only match history.
- Kaggle unofficial FIFA World Cup 2026 schedule: fallback fixture structure.
- World Football Elo Ratings: current national team Elo ratings.
- FBref World Cup stats: team and player stat tables when available.
- Manual CSVs: fallback templates in `data/raw/manual/`.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install requirements:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

Add credentials to `.env` only if you have them. Missing credentials will skip those sources instead of crashing the pipeline.

## Commands

Initialize folders, metadata, templates, and the starter team-name map:

```bash
python main.py init
```

Fetch all sources:

```bash
python main.py fetch --source all
```

Fetch one source:

```bash
python main.py fetch --source kaggle
python main.py fetch --source elo
python main.py fetch --source fbref
python main.py fetch --source fifa
python main.py fetch --source api-football
```

Clean available raw/manual files:

```bash
python main.py clean
```

Validate processed files:

```bash
python main.py validate
```

Build the modeling-ready match table:

```bash
python main.py build-master
```

Check credentials, manual fallbacks, and processed row readiness:

```bash
python main.py check-env
```

Load real data from API/Kaggle/online sources, falling back to manual CSVs when needed:

```bash
python main.py load-real-data
python main.py load-real-data --prefer manual
python main.py load-real-data --prefer api
python main.py load-real-data --skip-api
python main.py load-real-data --skip-kaggle
python main.py load-real-data --skip-fbref
python main.py load-real-data --skip-elo
```

Real-data loading writes:

```text
outputs/reports/source_status_report.md
outputs/reports/data_readiness_report.md
outputs/reports/manual_data_needed.md
outputs/reports/api_football_status.md
```

## Automatic Refresh Workflow

The automatic refresh workflow wraps the normal fetch, clean, build, and validate steps in one scheduler-friendly command. It is designed for matchday refreshes and repeated checks for newly completed matches.

Run the default matchday refresh:

```bash
python main.py update
```

This is equivalent to:

```bash
python main.py update --mode matchday
```

Run a completed-match check:

```bash
python main.py update --mode completed-match
```

Force a full refresh even if no new completed match is detected:

```bash
python main.py update --force
python main.py update --mode completed-match --force
```

### Refresh Modes

`matchday` mode is for daily or end-of-match-day updates. It fetches the latest available data, creates backups, cleans the data, rebuilds `matches_master.csv`, validates the processed files, updates state, and writes a refresh summary.

`completed-match` mode is for checks every 30 or 60 minutes. It first compares current completed match IDs against the previous update state. If no new completed match is found, it skips the expensive clean/build/validate work unless `--force` is used.

### Update State

Refresh state is stored in:

```text
data/metadata/update_state.json
```

It tracks the last refresh time, update mode, status, successful source, completed match IDs, result counts, fixture counts, and last error. If the file is missing, it is recreated. If it is corrupted, the corrupted file is backed up and a clean state file is created.

### Backups

Before a full refresh overwrites important processed files, timestamped backups are created under:

```text
data/backups/YYYYMMDD_HHMMSS/
```

Backed up files include fixtures, results, the master match dataset, ratings, team stats, and player stats. Backups are not deleted automatically, even if validation fails.

### Refresh Reports

Each update writes:

```text
outputs/reports/latest_refresh_summary.md
outputs/reports/latest_refresh_summary.json
outputs/reports/update_pipeline.log
```

The summary includes mode, source, API-key availability, fixture/result counts, new completed matches, updated files, backup folder, validation status, warnings, errors, and the next recommended action.

### API Keys

API-Football is preferred for live refreshes when `API_FOOTBALL_KEY` is set in `.env`. If the key is missing, the workflow uses existing processed/manual CSVs and logs a warning instead of crashing.

## After Adding API Keys

Add credentials only to `.env`. Never commit `.env`, paste keys into README, or save secret values in reports/logs.

Supported credentials:

```text
API_FOOTBALL_KEY=
API_FOOTBALL_WORLD_CUP_LEAGUE_ID=
KAGGLE_API_TOKEN=
KAGGLE_USERNAME=
KAGGLE_KEY=
SPORTMONKS_KEY=
```

Kaggle prefers `KAGGLE_API_TOKEN` when present, then falls back to `KAGGLE_USERNAME` plus `KAGGLE_KEY`.

Recommended verification flow:

```bash
python main.py check-env
python main.py diagnose-api-football
python main.py diagnose-kaggle
python main.py load-real-data --debug
python main.py data-summary
python main.py ready-for-features
python main.py update --mode matchday
```

`check-env` confirms hidden credential presence, folders, manual fallbacks, and processed row counts. `diagnose-api-football` and `diagnose-kaggle` test authentication without printing secrets. `load-real-data --debug` runs security checks, source diagnostics, loading, cleaning, master build, validation, summaries, and readiness reports. `data-summary` reports processed CSV row counts. `ready-for-features` writes the feature-readiness gate. `update --mode matchday` runs the scheduler-friendly refresh path.

Inspect these reports after loading:

```text
outputs/reports/security_check_report.md
outputs/reports/env_check_report.md
outputs/reports/api_football_diagnostic.md
outputs/reports/api_football_league_discovery.md
outputs/reports/kaggle_diagnostic.md
outputs/reports/kaggle_file_inventory.md
outputs/reports/elo_loading_status.md
outputs/reports/data_summary.md
outputs/reports/feature_readiness_gate.md
outputs/reports/data_readiness_report.md
```

Only start feature engineering after:

```text
READY_FOR_FEATURE_ENGINEERING = TRUE
```

If it is `FALSE`, open `outputs/reports/feature_readiness_gate.md` for the exact missing files and next action.

### Windows Task Scheduler

Create a task with:

```text
Program:
python

Arguments:
main.py update --mode matchday

Start in:
path/to/project/folder
```

For frequent completed-match polling, use:

```text
Arguments:
main.py update --mode completed-match
```

### Cron on Mac/Linux

Example daily matchday refresh at 11 PM:

```cron
0 23 * * * cd /path/to/dynamic-fifa-2026-predictor && python main.py update --mode matchday
```

Example completed-match polling every 30 minutes:

```cron
*/30 * * * * cd /path/to/dynamic-fifa-2026-predictor && python main.py update --mode completed-match
```

### GitHub Actions

The workflow file is:

```text
.github/workflows/update_data.yml
```

It can run manually with `workflow_dispatch` or on the editable cron schedule in the workflow file. Store `API_FOOTBALL_KEY`, `KAGGLE_USERNAME`, and `KAGGLE_KEY` as GitHub Secrets if you want the workflow to fetch live/API data. The workflow uploads `data/processed/`, `data/metadata/`, and `outputs/reports/` as artifacts.

The modeling and simulation phases are available. Later, this same update workflow can be extended to rerun predictions, full-bracket simulations, and dashboard outputs after the data refresh succeeds.

## Processed CSVs

- `data/processed/matches_master.csv`: combined historical matches plus completed 2026 results.
- `data/processed/fixtures_2026.csv`: standardized 2026 fixtures.
- `data/processed/results_2026.csv`: standardized completed 2026 results.
- `data/processed/team_ratings.csv`: FIFA ranking fields when available plus Elo ratings.
- `data/processed/team_stats_2026.csv`: team tournament stats from FBref/API/manual files.
- `data/processed/player_stats_2026.csv`: player tournament stats from FBref/API/manual files.
- `data/processed/team_name_map.csv`: raw-to-standard team name mappings.
- `outputs/reports/data_validation_report.csv`: validation results.
- `outputs/reports/fetch_pipeline.log`: fetch and cleaning log.

## Manual Fallbacks

If an API key is missing or a site blocks automated access, copy one of the templates in `data/raw/manual/`, remove `_template` from the filename, and fill it in. For example:

```text
data/raw/manual/manual_fixtures_2026.csv
data/raw/manual/manual_results_2026.csv
```

Then run:

```bash
python main.py clean
python main.py validate
python main.py build-master
```

## Known Limitations

- Some sources may block scraping or require JavaScript rendering.
- API keys may be required for live or complete data.
- The unofficial Kaggle 2026 schedule may differ from official FIFA data.
- Team names differ across sources and may need additions to `team_name_map.csv`.
- FBref tables can change structure, so the cleaner uses best-effort column matching.

## Next Steps

- Build the Streamlit dashboard.
- Replace fallback bracket mapping with official FIFA bracket/third-place placement rules when FIFA publishes or confirms them in a machine-readable source.

## Phase 3: Feature Engineering

Feature engineering turns cleaned match, fixture, and rating data into model-ready tables. This phase does not train a model; it prepares safe inputs for the later modeling phase.

Before creating features, the pipeline creates feature-specific cleaned copies of the data. It does not overwrite `data/processed/matches_master.csv`. Duplicate historical matches are inspected and cleaned only for feature use because repeated rows can bias a model.

FIFA 2026 fixtures with unknown teams are kept. They are marked with TBD flags and `is_predictable_now = False` until both teams and required features are known. This preserves them for later tournament simulation without pretending they are currently predictable.

Leakage means accidentally using information that would not have been known before a match, such as current match goals, post-match Elo, or future results. The feature pipeline records pre-match Elo and shifted rolling form so the current match does not predict itself.

Feature groups created:

- Chronological Elo features
- Recent form features
- Goal and defensive performance features
- Current rating features for 2026 fixtures
- Head-to-head features
- Tournament context features
- Schedule and rest features

Run Phase 3:

```bash
python main.py feature-data-quality
python main.py build-features
python main.py validate-features
python main.py feature-summary
```

Important outputs:

```text
data/features/intermediate/matches_master_feature_clean.csv
data/features/intermediate/fixtures_2026_feature_clean.csv
data/features/intermediate/team_match_history.csv
data/features/final/match_training_dataset.csv
data/features/final/fixture_2026_features.csv
outputs/reports/features/feature_validation_report.md
outputs/reports/features/leakage_check_report.md
outputs/reports/features/feature_dictionary.md
outputs/reports/features/feature_build_summary.md
```

Only build the prediction model after feature validation and leakage checks pass or any remaining warnings are explicitly accepted.

## Phase 4: Modeling

The modeling phase predicts the match outcome from Team A's perspective:

```text
0 = team_a_loss
1 = draw
2 = team_a_win
```

The primary evaluation split is chronological, not random. Older matches train the model, the next slice validates model choice, and the newest slice is held out for final testing. This better matches the real task: predicting future football matches from past information.

Baseline models matter because they tell us whether machine-learning models add value beyond simple class frequencies or Elo difference. The pipeline trains majority-class, historical-frequency, Elo-logistic, Logistic Regression, and XGBoost models.

Because the project needs probabilities for later tournament simulation, log loss and multiclass Brier score matter more than accuracy. Accuracy only checks the top class; log loss and Brier score evaluate probability quality.

Logistic Regression is the simpler interpretable model. XGBoost is the stronger nonlinear model. The selected model is chosen by lowest validation log loss, with test metrics reported separately.

Fixture predictions are generated only for rows where `is_predictable_now = True`. TBD fixtures remain in the prediction file but are marked not predictable until the teams and required features are known.

Run Phase 4:

```bash
python main.py modeling-data-summary
python main.py train-models
python main.py evaluate-models
python main.py predict-fixtures
python main.py modeling-summary
```

Important outputs:

```text
outputs/models/logistic_regression_model.joblib
outputs/models/xgboost_match_outcome_model.joblib
outputs/models/selected_model.joblib
outputs/models/model_registry.json
outputs/predictions/fixture_2026_match_predictions.csv
outputs/reports/modeling/model_comparison.md
outputs/reports/modeling/modeling_phase_summary.md
```

Monte Carlo tournament simulation comes after this phase. It is not built here.

## Phase 5: Monte Carlo Tournament Simulation

Monte Carlo simulation means running the tournament thousands of times by sampling each match from model probabilities. The repeated runs estimate how often each team reaches later rounds.

For group-stage matches, the simulator samples one of three outcomes:

```text
team_a_loss
draw
team_a_win
```

Group-stage draws are allowed and award one point to each team. Knockout matches cannot end in a draw, so draw probability is split evenly into advancement probability:

```text
team_a_advancement = prob_team_a_win + 0.5 * prob_draw
team_b_advancement = prob_team_a_loss + 0.5 * prob_draw
```

TBD fixtures are difficult because the current data preserves future placeholders such as playoff winners and unresolved knockout slots. The simulator does not treat TBD as a real team and does not invent bracket mapping silently.

Partial mode remains available for conservative simulations that do not force unresolved bracket paths. Full-bracket mode uses the explicit Phase 5B fallback mapping and clearly reports that this mapping is not official FIFA bracket placement.

Run Phase 5:

```bash
python main.py simulation-input-summary
python main.py run-simulation --mode partial --n-simulations 10000
python main.py validate-simulation
python main.py simulation-summary
```

Important outputs:

```text
outputs/simulations/team_advancement_probabilities.csv
outputs/simulations/champion_probabilities.csv
outputs/simulations/stage_probability_summary.csv
outputs/simulations/simulated_match_results_sample.csv
outputs/reports/simulation/monte_carlo_summary.md
outputs/reports/simulation/simulation_limitations.md
```

## Phase 5B: Bracket Mapping and Full Champion Simulation

Phase 5B adds explicit bracket CSVs and a full-bracket simulation mode. The current mapping is a transparent fallback template, not an official FIFA knockout or third-place placement rule.

Bracket mapping files:

```text
data/bracket/fifa_2026_bracket_slots.csv
data/bracket/fifa_2026_round_progression.csv
data/bracket/fifa_2026_third_place_mapping.csv
```

Run bracket inspection and validation:

```bash
python main.py inspect-bracket
python main.py validate-bracket
python main.py bracket-summary
```

Run full champion simulation:

```bash
python main.py run-simulation --mode full-bracket --n-simulations 10000
python main.py validate-simulation
python main.py champion-summary
```

`--mode auto` selects full-bracket mode when the bracket mapping validates; otherwise it falls back to partial mode.

Additional outputs:

```text
outputs/simulations/bracket_completion_summary.csv
outputs/simulations/probability_source_summary.csv
outputs/reports/simulation/bracket/bracket_source_report.md
outputs/reports/simulation/bracket/bracket_validation_report.md
outputs/reports/simulation/bracket/full_champion_simulation_summary.md
```

The latest verified full-bracket run completed 10,000 of 10,000 simulations with champion probabilities summing to 1.0. Most generated knockout matchups used Elo fallback probabilities because exact model predictions only exist for currently known scheduled fixtures.

The dashboard comes after simulation outputs exist. It is not built in this phase.

## Phase 5C: Live Tournament State and Finalist Prediction

Phase 5C forecasts likely finalists and champion probabilities from the current tournament state. It differs from earlier modes:

- Static pre-tournament prediction uses the fixture prediction file as it exists before matches are played.
- Partial simulation keeps unresolved paths conservative.
- Fallback full-bracket simulation uses a transparent fallback bracket template.
- Live tournament-state simulation fetches current fixtures/results/standings when available, locks completed results, uses known bracket fixtures where available, and falls back only where live/official structure is unavailable.

Run the live workflow:

```bash
python main.py fetch-live-state
python main.py build-live-state
python main.py run-live-forecast --n-simulations 10000
python main.py validate-live-forecast
python main.py live-forecast-summary
```

Run after a matchday refresh:

```bash
python main.py update --mode matchday --run-live-forecast --n-simulations 10000 --no-retrain
```

The live forecast writes:

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
```

Reports:

```text
outputs/reports/live_state/api_football_live_status.md
outputs/reports/live_state/fifa_official_live_status.md
outputs/reports/live_state/live_state_summary.md
outputs/reports/live_state/standings_status_report.md
outputs/reports/live_state/live_bracket_source_report.md
outputs/reports/live_state/finalist_prediction_summary.md
outputs/reports/live_state/live_update_limitations.md
outputs/reports/live_state/live_validation_report.md
outputs/reports/live_state/end_of_matchday_update_summary.md
```

Completed results are treated as fixed truth and are not overwritten by simulation. Remaining matches use saved model predictions when available, then dynamic model lookup, then Elo fallback, then neutral fallback if needed.

Finalist-pair probabilities count `Argentina vs Spain` and `Spain vs Argentina` as the same pair. Finalist predictions are active until finalists are officially known; once the tournament reaches the final, the system reports known finalists and focuses on champion probability if the final has not been completed.

Limitations:

- API-Football availability depends on credentials, plan access, and whether FIFA 2026 data is exposed yet.
- FIFA official pages are checked politely; the project does not bypass JavaScript rendering or blocks.
- Fallback bracket usage is clearly reported and is not official FIFA mapping.
- Missing team/player stats can limit newly generated matchup features.
- Predictions are probabilities, not guarantees.

## Phase 5D: True-Live Forecast Verification

Phase 5D adds the honesty gate for live forecasting. It verifies whether the project is really using current FIFA 2026 live fixtures/results/standings/bracket data, or whether it is only running a fallback pre-tournament scenario.

Forecast modes:

- `true_live_forecast`: live fixtures/results are available, current phase has real tournament state, standings/bracket coverage is strong enough.
- `partially_live_forecast`: some live current-state data is available, but standings or bracket still depend on computed/fallback assumptions.
- `fallback_pre_tournament_forecast`: no completed 2026 results are detected and fallback bracket assumptions dominate.
- `insufficient_data`: no reliable current live state is available.

Fallback-only forecasts are useful for testing, but they must not be called true live forecasts. By default, `run-live-forecast` now refuses to produce fallback-only finalist predictions unless explicitly allowed.

Source priority:

1. API-Football live API
2. FIFA official source, when parseable without aggressive scraping
3. Secondary public sources for sanity-check reports only
4. Local processed CSV fallback
5. Fallback bracket template as last-resort structure only

Run true-live diagnostics and quality gate:

```bash
python main.py diagnose-live-api
python main.py verify-live-sources
python main.py live-quality-gate
python main.py live-source-summary
```

Run the gated forecast:

```bash
python main.py run-live-forecast --n-simulations 10000
```

Run fallback explicitly for testing:

```bash
python main.py run-live-forecast --n-simulations 10000 --allow-fallback-forecast
```

Run matchday update with the gate:

```bash
python main.py update --mode matchday --run-live-forecast --n-simulations 10000
python main.py update --mode matchday --run-live-forecast --allow-fallback-forecast --n-simulations 10000
```

New verification outputs:

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
```

The final-team prediction should only be considered truly live if the quality gate says `true_live_forecast` or `partially_live_forecast`. If it says `fallback_pre_tournament_forecast`, the output is a labeled testing/fallback scenario, not a live tournament-state claim.

## Football-data.org Provider

football-data.org is an alternative live-data provider for FIFA World Cup data when API-Football blocks 2026 data by plan or season access.

Add these values to local `.env`:

```text
FOOTBALL_DATA_ORG_KEY=
FOOTBALL_DATA_ORG_COMPETITION_ID=2000
FOOTBALL_DATA_ORG_COMPETITION_CODE=WC
FOOTBALL_DATA_ORG_SEASON=2026
```

To get a token, sign up at football-data.org, copy your API token, and add it to local `.env` as `FOOTBALL_DATA_ORG_KEY=...`. Never commit `.env`, paste the token into reports, or put a real key in `.env.example`.

Test football-data.org:

```bash
python main.py diagnose-football-data-org
python main.py fetch-football-data-org
python main.py normalize-football-data-org
python main.py diagnose-live-providers
python main.py select-live-provider
python main.py live-source-summary
python main.py live-quality-gate
```

Run the gated forecast:

```bash
python main.py run-live-forecast --n-simulations 1000
```

football-data.org outputs:

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

Caveats:

- football-data.org may or may not expose 2026 World Cup rows on the available tier.
- Repeated diagnostics can hit rate limits; normalized outputs preserve the last good provider data and can be rebuilt from saved sanitized snapshots.
- Standings may be unavailable and may need to be computed from completed group matches.
- Bracket mapping may still require fallback if knockout pairings are not available.
- Schedule-only data is not a true live tournament forecast.
- Forecast labels always come from the quality gate.
