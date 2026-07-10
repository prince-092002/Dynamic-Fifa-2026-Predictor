# Automatic Refresh Workflow Handoff

Project: Dynamic FIFA 2026 Tournament Outcome Predictor  
Date: 2026-07-04  
Scope completed: Phase 2 automatic data refresh workflow only.

## Summary

Added a scheduler-friendly update system so the project can refresh data with one command:

```bash
python main.py update --mode matchday
```

Also added completed-match polling:

```bash
python main.py update --mode completed-match
```

And forced refresh support:

```bash
python main.py update --force
python main.py update --mode completed-match --force
```

No prediction model, feature engineering, Monte Carlo simulator, or Streamlit dashboard was built.

## Files Added

- `src/update/__init__.py`
- `src/update/update_state.py`
- `src/update/update_runner.py`
- `src/update/backup_manager.py`
- `src/update/refresh_report.py`
- `scripts/update_matchday.py`
- `scripts/update_completed_match.py`
- `.github/workflows/update_data.yml`

## Files Updated

- `main.py`
- `README.md`
- `src/config.py`
- `src/utils/files.py`

## New Folders Added

- `data/backups/`
- `src/update/`
- `scripts/`
- `.github/workflows/`

## Key Features

- New `main.py update` CLI command.
- Matchday refresh mode.
- Completed-match polling mode.
- `--force` support.
- API-Football preferred when `API_FOOTBALL_KEY` exists.
- Existing processed/manual CSV fallback when API key is missing.
- New completed match detection from normalized match statuses.
- Fallback match key when `match_id` is missing.
- Timestamped backups before full refresh overwrites.
- Persistent update state in `data/metadata/update_state.json`.
- Markdown and JSON refresh reports.
- Dedicated update log at `outputs/reports/update_pipeline.log`.
- Scheduler scripts for Windows Task Scheduler, cron, or similar tools.
- GitHub Actions workflow with manual and scheduled runs.

## Status Normalization

The update workflow normalizes statuses into:

- `scheduled`
- `live`
- `completed`
- `postponed`
- `cancelled`
- `unknown`

Completed status examples include:

- `completed`
- `finished`
- `ft`
- `match finished`

## Outputs Created by Update Workflow

- `data/metadata/update_state.json`
- `outputs/reports/latest_refresh_summary.md`
- `outputs/reports/latest_refresh_summary.json`
- `outputs/reports/update_pipeline.log`
- `data/backups/<timestamp_folder>/`

## Smoke Tests Run

These commands passed:

```bash
python -m compileall src main.py scripts
python main.py update --mode completed-match
python main.py update --mode matchday
python main.py update --mode completed-match --force
python scripts/update_completed_match.py
python scripts/update_matchday.py
```

Current environment has no `API_FOOTBALL_KEY`, so the workflow correctly used existing processed/manual CSVs and logged warnings instead of crashing.

## Current Behavior Without API Key

- `completed-match` mode checks existing processed results.
- If no new completed match is found, it skips rebuild.
- `matchday` mode still creates backups and runs clean/build/validate.
- Reports and update state are still written.

## Next Steps

1. Add `API_FOOTBALL_KEY` to `.env` when available.
2. Run:

```bash
python main.py update --mode matchday
```

3. Inspect:

- `outputs/reports/latest_refresh_summary.md`
- `outputs/reports/update_pipeline.log`
- `data/metadata/update_state.json`

4. After real data exists, expand team-name mappings if `outputs/reports/unmapped_team_names.csv` is created.

