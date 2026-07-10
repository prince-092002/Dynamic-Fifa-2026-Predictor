# Data Foundation Handoff

Project: Dynamic FIFA 2026 Tournament Outcome Predictor  
Date: 2026-07-04  
Scope completed: data fetching, cleaning, validation, metadata, and CLI foundation only.

## Summary

The project now has a working Python data pipeline foundation for FIFA World Cup 2026 and historical international football data. The prediction model, Monte Carlo simulator, and Streamlit dashboard were intentionally not built yet.

The pipeline can initialize folders, create manual fallback templates, fetch supported sources when credentials/network access are available, clean available data into standardized CSV schemas, validate processed data, and build a combined match master dataset.

## Folder Structure Created

- `data/raw/kaggle/`
- `data/raw/fifa/`
- `data/raw/fbref/`
- `data/raw/elo/`
- `data/raw/api_football/`
- `data/raw/manual/`
- `data/processed/`
- `data/metadata/`
- `src/fetch/`
- `src/cleaning/`
- `src/validation/`
- `src/utils/`
- `notebooks/`
- `outputs/reports/`
- `handoff/`

## Main Files Created

- `main.py`
- `README.md`
- `requirements.txt`
- `.env.example`
- `notebooks/data_check.ipynb`
- `src/config.py`
- `src/logger.py`
- `src/utils/files.py`
- `src/utils/http.py`
- `src/utils/dates.py`
- `src/fetch/fetch_kaggle.py`
- `src/fetch/fetch_fifa.py`
- `src/fetch/fetch_fbref.py`
- `src/fetch/fetch_elo.py`
- `src/fetch/fetch_api_football.py`
- `src/fetch/fetch_all.py`
- `src/cleaning/clean_matches.py`
- `src/cleaning/clean_team_stats.py`
- `src/cleaning/clean_player_stats.py`
- `src/cleaning/standardize_team_names.py`
- `src/cleaning/build_master_dataset.py`
- `src/validation/validate_data.py`

## Fetching Tasks Completed

Implemented Kaggle fetch support:

- `download_kaggle_dataset(dataset_slug, output_dir)`
- `fetch_international_results()`
- `fetch_world_cup_historical()`
- `fetch_world_cup_2026_schedule()`

Behavior:

- Uses Kaggle API when `KAGGLE_USERNAME` and `KAGGLE_KEY` are present.
- Skips gracefully when credentials are missing.
- Logs manual download instructions.
- Saves raw files under `data/raw/kaggle/`.

Implemented FIFA Data Centre support:

- `fetch_fifa_data_centre_matches()`
- `clean_fifa_matches()`

Behavior:

- Attempts to parse FIFA match page as static HTML.
- If parsing fails due to JavaScript rendering or blocking, writes a clear fallback note.
- Does not use Selenium or aggressive scraping.

Implemented API-Football support:

- `api_football_request(endpoint, params)`
- `fetch_api_football_fixtures_2026()`
- `fetch_api_football_results_2026()`
- `fetch_api_football_teams_2026()`
- `fetch_api_football_standings_2026()`
- `fetch_api_football_team_stats_2026()`

Also added aliases matching the requested shorter names:

- `fetch_api_football_fixtures`
- `fetch_api_football_results`
- `fetch_api_football_teams`
- `fetch_api_football_standings`
- `fetch_api_football_team_stats`

Behavior:

- Uses `API_FOOTBALL_KEY` from `.env`.
- Skips gracefully when the key is missing.
- Saves raw JSON under `data/raw/api_football/`.
- Converts fixture/result responses into processed CSVs when data is available.

Implemented Elo support:

- `fetch_world_football_elo()`

Behavior:

- Attempts to parse `https://eloratings.net/`.
- Saves raw Elo data to `data/raw/elo/world_football_elo_current.csv`.
- Saves cleaned ratings to `data/processed/team_ratings.csv`.

Implemented FBref support:

- `fetch_fbref_table(url, output_path)`
- `fetch_fbref_world_cup_2026_all_stats()`
- `clean_fbref_team_stats()`
- `clean_fbref_player_stats()`

Behavior:

- Uses polite request handling.
- Handles tables inside HTML comments.
- Adds delays between requests.
- Saves raw tables under `data/raw/fbref/`.
- Writes warning fallback if blocked or unavailable.

Implemented all-source fetch orchestration:

- `fetch_all_sources()`

Behavior:

- Runs sources in a safe order.
- Catches per-source failures.
- Prints a summary table.
- Logs outcomes to `data/metadata/fetch_log.csv`.

## Cleaning Tasks Completed

Implemented match cleaners:

- `clean_historical_international_matches()`
- `clean_historical_world_cup_matches()`
- `clean_2026_fixtures()`
- `clean_2026_results()`

Implemented master dataset builder:

- `build_matches_master()`

Behavior:

- Combines historical international matches, historical World Cup matches, and completed 2026 results.
- Standardizes team names.
- Parses dates.
- Adds `winner` and `is_draw`.
- Generates missing `match_id` values.
- Deduplicates match rows.
- Saves `data/processed/matches_master.csv`.

Implemented team/player stat fallback cleaners:

- `clean_manual_team_ratings()`
- `clean_manual_team_stats()`
- `clean_manual_player_stats()`

Behavior:

- Uses existing processed files if they contain rows.
- Falls back to manual CSV templates if no source data exists.

## Team Name Standardization Completed

Implemented:

- `basic_clean_team_name()`
- `load_team_name_map()`
- `standardize_team_name()`
- `standardize_team_columns()`
- `initialize_team_name_map()`

Included built-in examples:

- `USA` -> `United States`
- `USMNT` -> `United States`
- `Korea Republic` -> `South Korea`
- `IR Iran` -> `Iran`
- `Côte d'Ivoire` -> `Ivory Coast`
- `Czechia` -> `Czech Republic`
- `Türkiye` -> `Turkey`

Unknown names are written to:

- `outputs/reports/unmapped_team_names.csv`

## Validation Tasks Completed

Implemented:

- `validate_matches_master()`
- `validate_fixtures_2026()`
- `validate_results_2026()`
- `validate_team_ratings()`
- `validate_team_stats_2026()`
- `run_all_validations()`

Validation checks include:

- Required columns exist.
- Dates are parseable.
- Goals and ratings are numeric.
- Team names are not null.
- Duplicate `match_id` values are detected.
- Duplicate same-date same-team match rows are detected.
- Fixture statuses are valid.
- Completed results have goals and winners.

Validation report output:

- `outputs/reports/data_validation_report.csv`

## Metadata and Logging Completed

Created:

- `data/metadata/data_sources.csv`
- `data/metadata/fetch_log.csv`
- `outputs/reports/fetch_pipeline.log`

Fetch log columns:

- `timestamp`
- `source`
- `source_url`
- `status`
- `rows_fetched`
- `raw_output_path`
- `processed_output_path`
- `notes`

## Manual Fallback Templates Created

Created in `data/raw/manual/`:

- `manual_fixtures_2026_template.csv`
- `manual_results_2026_template.csv`
- `manual_team_ratings_template.csv`
- `manual_team_stats_2026_template.csv`
- `manual_player_stats_2026_template.csv`

The project can run with only manual CSVs available.

## CLI Commands Implemented

Available commands:

```bash
python main.py init
python main.py fetch --source all
python main.py fetch --source kaggle
python main.py fetch --source elo
python main.py fetch --source fbref
python main.py fetch --source fifa
python main.py fetch --source api-football
python main.py clean
python main.py validate
python main.py build-master
```

## Smoke Tests Run

The following commands were run successfully:

```bash
python -m compileall src main.py
python main.py init
python main.py clean
python main.py build-master
python main.py validate
python main.py fetch --source kaggle
python main.py fetch --source api-football
```

Observed behavior:

- Code compiles.
- Initialization creates folders, metadata, templates, and team-name map.
- Cleaning creates all expected processed CSVs.
- Master dataset builds successfully.
- Validation report is created with no failures for header-only fallback data.
- Kaggle fetch skips cleanly when credentials are missing.
- API-Football fetch skips cleanly when `API_FOOTBALL_KEY` is missing.

## Current Output State

The following processed files exist:

- `data/processed/matches_master.csv`
- `data/processed/fixtures_2026.csv`
- `data/processed/results_2026.csv`
- `data/processed/team_ratings.csv`
- `data/processed/team_stats_2026.csv`
- `data/processed/player_stats_2026.csv`
- `data/processed/team_name_map.csv`
- `data/processed/historical_international_matches.csv`
- `data/processed/historical_world_cup_matches.csv`

Most data files are currently header-only because no live credentials or downloaded source datasets have been added yet.

## Known Limitations

- Network-dependent fetches require installed dependencies from `requirements.txt`.
- Kaggle datasets require `KAGGLE_USERNAME` and `KAGGLE_KEY`, or manual downloads.
- API-Football requires `API_FOOTBALL_KEY`.
- FIFA Data Centre may be JavaScript-rendered and may not be parseable as static HTML.
- FBref may block automated requests or change table structures.
- The unofficial Kaggle 2026 schedule may differ from official FIFA data.
- Team-name mappings will need expansion after real data is loaded.

## Recommended Next Steps

1. Install requirements:

```bash
pip install -r requirements.txt
```

2. Create `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

3. Add available credentials:

```text
API_FOOTBALL_KEY=
KAGGLE_USERNAME=
KAGGLE_KEY=
```

4. Fetch source data:

```bash
python main.py fetch --source all
```

5. Clean and validate:

```bash
python main.py clean
python main.py validate
python main.py build-master
```

6. Inspect:

- `outputs/reports/fetch_pipeline.log`
- `outputs/reports/data_validation_report.csv`
- `outputs/reports/unmapped_team_names.csv`

7. After the data foundation has real rows, begin the next phase:

- Elo feature engineering
- ML feature set
- XGBoost model
- Monte Carlo tournament simulator
- Streamlit dashboard

