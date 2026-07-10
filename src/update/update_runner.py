"""Automatic update workflow for matchday and completed-match checks."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import pandas as pd

from src.cleaning.build_master_dataset import build_matches_master
from src.cleaning.clean_matches import run_all_match_cleaners
from src.cleaning.clean_player_stats import clean_manual_player_stats
from src.cleaning.clean_team_stats import clean_manual_team_ratings, clean_manual_team_stats
from src.cleaning.standardize_team_names import initialize_team_name_map
from src.config import (
    API_FOOTBALL_KEY,
    PROCESSED_DIR,
    RAW_API_FOOTBALL_DIR,
    UPDATE_LOG_PATH,
    ensure_project_directories,
)
from src.fetch.fetch_api_football import (
    WORLD_CUP_LEAGUE_ID,
    WORLD_CUP_SEASON,
    api_football_request,
    fetch_api_football_fixtures_2026,
    fetch_api_football_results_2026,
)
from src.update.backup_manager import create_backups_for_processed_files
from src.update.refresh_report import write_refresh_summary
from src.update.update_state import load_update_state, save_update_state
from src.utils.dates import now_utc_iso, parse_date_series
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    RESULTS_2026_COLUMNS,
    initialize_metadata_files,
    read_csv_if_exists,
)
from src.validation.validate_data import run_all_validations


COMPLETED_STATUSES = {"completed", "finished", "ft", "match finished", "aet", "pen", "full time"}
LIVE_STATUSES = {"live", "in progress", "1h", "2h", "ht", "et", "p", "bt"}
POSTPONED_STATUSES = {"postponed", "pst", "suspended", "int"}
CANCELLED_STATUSES = {"cancelled", "canceled", "abandoned", "awd"}
SCHEDULED_STATUSES = {"scheduled", "not started", "ns", "tbd", "time to be defined"}


def get_update_logger() -> logging.Logger:
    """Return the update workflow logger."""
    ensure_project_directories()
    logger = logging.getLogger("fifa_update_pipeline")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        UPDATE_LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


logger = get_update_logger()


def normalize_match_status(status: object) -> str:
    """Normalize source-specific status labels into a small stable set."""
    if pd.isna(status):
        return "unknown"
    text = str(status).strip().lower()
    if not text:
        return "unknown"
    if text in COMPLETED_STATUSES:
        return "completed"
    if text in LIVE_STATUSES:
        return "live"
    if text in POSTPONED_STATUSES:
        return "postponed"
    if text in CANCELLED_STATUSES:
        return "cancelled"
    if text in SCHEDULED_STATUSES:
        return "scheduled"
    return "unknown"


def _match_key(row: pd.Series) -> str:
    match_id = row.get("match_id")
    if pd.notna(match_id) and str(match_id).strip():
        return str(match_id).strip()
    parts = [
        row.get("date", ""),
        row.get("team_a", ""),
        row.get("team_b", ""),
        row.get("stage", ""),
    ]
    return "|".join(str(part).strip().lower() for part in parts)


def detect_new_completed_matches(
    current_results_df: pd.DataFrame,
    previous_completed_match_ids: list[str],
) -> tuple[pd.DataFrame, list[str], int]:
    """Return completed rows that were not present in the previous update state."""
    if current_results_df.empty:
        return current_results_df.copy(), [], 0
    results = current_results_df.copy()
    if "status" not in results.columns:
        results["status"] = "completed"
    results["normalized_status"] = results["status"].apply(normalize_match_status)
    completed = results[results["normalized_status"].eq("completed")].copy()
    if completed.empty:
        return completed, [], 0
    completed["completed_match_key"] = completed.apply(_match_key, axis=1)
    all_ids = completed["completed_match_key"].dropna().astype(str).tolist()
    previous = {str(match_id) for match_id in previous_completed_match_ids}
    new_rows = completed[~completed["completed_match_key"].isin(previous)].copy()
    new_ids = new_rows["completed_match_key"].dropna().astype(str).tolist()
    return new_rows, all_ids, len(new_ids)


def _api_fixture_rows(data: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in data.get("response", []):
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        status_obj = fixture.get("status", {})
        raw_status = status_obj.get("long") or status_obj.get("short")
        rows.append(
            {
                "match_id": fixture.get("id"),
                "date": fixture.get("date"),
                "stage": league.get("round"),
                "group": pd.NA,
                "team_a": teams.get("home", {}).get("name"),
                "team_b": teams.get("away", {}).get("name"),
                "venue": fixture.get("venue", {}).get("name"),
                "city": fixture.get("venue", {}).get("city"),
                "country": "Canada/Mexico/United States",
                "status": normalize_match_status(raw_status),
                "team_a_goals": goals.get("home"),
                "team_b_goals": goals.get("away"),
                "source": "api_football",
                "last_updated": now_utc_iso(),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "match_id",
            "date",
            "stage",
            "group",
            "team_a",
            "team_b",
            "venue",
            "city",
            "country",
            "status",
            "team_a_goals",
            "team_b_goals",
            "source",
            "last_updated",
        ],
    )


def _fetch_candidate_api_data(warnings: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Fetch latest API-Football data without overwriting processed CSVs."""
    if not API_FOOTBALL_KEY:
        warnings.append("API_FOOTBALL_KEY is missing; using existing processed/manual CSVs.")
        fixtures = read_csv_if_exists(PROCESSED_DIR / "fixtures_2026.csv", FIXTURES_2026_COLUMNS)
        results = read_csv_if_exists(PROCESSED_DIR / "results_2026.csv", RESULTS_2026_COLUMNS)
        return fixtures, results, "existing_processed_csv"

    data = api_football_request(
        "fixtures",
        {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON},
    )
    RAW_API_FOOTBALL_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_API_FOOTBALL_DIR / "latest_update_fixtures_2026.json"
    raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    fixtures = _api_fixture_rows(data)
    if fixtures.empty:
        warnings.append("API-Football returned 0 fixture rows; using existing processed CSVs.")
        existing_fixtures = read_csv_if_exists(PROCESSED_DIR / "fixtures_2026.csv", FIXTURES_2026_COLUMNS)
        existing_results = read_csv_if_exists(PROCESSED_DIR / "results_2026.csv", RESULTS_2026_COLUMNS)
        return existing_fixtures, existing_results, "existing_processed_csv"
    results = fixtures[fixtures["status"].eq("completed")].copy()
    if not results.empty:
        results["team_a_goals"] = pd.to_numeric(results["team_a_goals"], errors="coerce")
        results["team_b_goals"] = pd.to_numeric(results["team_b_goals"], errors="coerce")
        results["winner"] = results.apply(
            lambda row: row["team_a"]
            if row["team_a_goals"] > row["team_b_goals"]
            else row["team_b"]
            if row["team_b_goals"] > row["team_a_goals"]
            else "Draw",
            axis=1,
        )
        results["is_draw"] = results["winner"].eq("Draw")
    return fixtures, results, "api_football"


def _run_full_refresh(source_used: str, files_updated: list[str], warnings: list[str]) -> tuple[str, int]:
    """Fetch when possible, then clean, build, and validate."""
    if API_FOOTBALL_KEY:
        fetch_api_football_fixtures_2026()
        fetch_api_football_results_2026()
    else:
        warnings.append("Full refresh skipped API fetch because API_FOOTBALL_KEY is missing.")

    clean_outputs = run_all_match_cleaners()
    clean_outputs.extend([clean_manual_team_ratings(), clean_manual_team_stats(), clean_manual_player_stats()])
    master_output = build_matches_master()
    validation_report = run_all_validations()
    files_updated.extend([str(path) for path in clean_outputs])
    files_updated.extend([master_output, validation_report])

    validation_df = read_csv_if_exists(Path(validation_report), [])
    failed_checks = int(validation_df["status"].eq("fail").sum()) if "status" in validation_df.columns else 0
    validation_status = "failed" if failed_checks else "passed"
    return validation_status, failed_checks


def _update_state_after_run(
    state: dict[str, Any],
    mode: str,
    status: str,
    source_used: str,
    completed_match_ids: list[str],
    latest_result_count: int,
    latest_fixture_count: int,
    last_error: str = "",
) -> None:
    state.update(
        {
            "last_refresh_time": now_utc_iso(),
            "last_update_mode": mode,
            "last_update_status": status,
            "last_successful_source": source_used if status in {"success", "skipped"} else state.get("last_successful_source", ""),
            "last_completed_match_ids": sorted({str(match_id) for match_id in completed_match_ids if str(match_id).strip()}),
            "latest_result_count": int(latest_result_count),
            "latest_fixture_count": int(latest_fixture_count),
            "last_error": last_error,
        }
    )
    save_update_state(state)


def run_update(mode: str = "matchday", force: bool = False, run_live_forecast: bool = False, n_simulations: int = 10000, no_retrain: bool = False, allow_fallback_forecast: bool = False) -> dict[str, Any]:
    """Run the scheduler-friendly automatic refresh workflow."""
    if mode not in {"matchday", "completed-match"}:
        raise ValueError("mode must be 'matchday' or 'completed-match'")

    ensure_project_directories()
    initialize_metadata_files()
    initialize_team_name_map()

    state = load_update_state()
    warnings: list[str] = []
    errors: list[str] = []
    files_updated: list[str] = []
    backup_folder = ""
    refresh_timestamp = now_utc_iso()
    source_used = "unknown"
    fixtures_fetched = 0
    completed_results_count = 0
    new_count = 0
    completed_match_ids: list[str] = state.get("last_completed_match_ids", [])
    validation_status = "not_run"
    live_forecast_result: dict[str, Any] | None = None

    logger.info("Update started | mode=%s | force=%s | api_key_available=%s", mode, force, bool(API_FOOTBALL_KEY))

    try:
        candidate_fixtures, candidate_results, source_used = _fetch_candidate_api_data(warnings)
        fixtures_fetched = len(candidate_fixtures)
        completed_results_count = len(candidate_results)
        previous_ids = [str(match_id) for match_id in state.get("last_completed_match_ids", [])]
        _, completed_match_ids, new_count = detect_new_completed_matches(candidate_results, previous_ids)
        logger.info("Detected %s new completed matches from %s", new_count, source_used)

        should_full_refresh = mode == "matchday" or force or new_count > 0
        if should_full_refresh:
            backup_folder = str(create_backups_for_processed_files())
            logger.info("Backups created at %s", backup_folder)
            validation_status, failed_checks = _run_full_refresh(source_used, files_updated, warnings)

            refreshed_results = read_csv_if_exists(PROCESSED_DIR / "results_2026.csv", RESULTS_2026_COLUMNS)
            _, completed_match_ids, _ = detect_new_completed_matches(refreshed_results, previous_ids)
            completed_results_count = len(refreshed_results)
            if failed_checks:
                warnings.append(f"Validation completed with {failed_checks} failing checks. Backups were kept at {backup_folder}.")
            update_status = "success" if validation_status == "passed" else "validation_failed"
            next_action = "Review validation failures before using refreshed data." if failed_checks else "Data refresh complete. Ready for the next modeling phase when needed."
        else:
            update_status = "skipped"
            next_action = "No new completed match detected. Keep the scheduler running or use --force for a full refresh."

        _update_state_after_run(
            state=state,
            mode=mode,
            status=update_status,
            source_used=source_used,
            completed_match_ids=completed_match_ids,
            latest_result_count=completed_results_count,
            latest_fixture_count=fixtures_fetched,
        )
        if run_live_forecast:
            try:
                if not no_retrain:
                    try:
                        from src.modeling.predict_fixtures import predict_fixtures

                        prediction_result = predict_fixtures()
                        files_updated.append(str(prediction_result.get("predictions", "")))
                    except Exception as exc:
                        warnings.append(f"Prediction refresh could not run; live forecast will use existing predictions and fallbacks. Reason: {exc}")
                from src.live_state.live_pipeline import run_live_forecast_pipeline
                from src.live_state.live_reports import write_end_of_matchday_update_summary

                live_forecast_result = run_live_forecast_pipeline(n_simulations=n_simulations, allow_fallback_forecast=allow_fallback_forecast)
                files_updated.append(write_end_of_matchday_update_summary({"validation_status": validation_status, "new_completed_matches_detected": new_count}, live_forecast_result))
            except Exception as exc:
                warnings.append(f"Live finalist forecast failed after update: {exc}")
    except Exception as exc:
        errors.append(str(exc))
        logger.exception("Update workflow failed")
        _update_state_after_run(
            state=state,
            mode=mode,
            status="failed",
            source_used=source_used,
            completed_match_ids=completed_match_ids,
            latest_result_count=completed_results_count,
            latest_fixture_count=fixtures_fetched,
            last_error=str(exc),
        )
        next_action = "Check outputs/reports/update_pipeline.log and rerun after fixing the reported issue."

    result = {
        "refresh_timestamp": refresh_timestamp,
        "mode": mode,
        "force": force,
        "source_used": source_used,
        "api_key_available": bool(API_FOOTBALL_KEY),
        "fixtures_fetched": fixtures_fetched,
        "completed_results_count": completed_results_count,
        "new_completed_matches_detected": new_count,
        "files_updated": files_updated,
        "backup_folder": backup_folder,
        "validation_status": validation_status,
        "warnings": warnings,
        "errors": errors,
        "next_recommended_action": next_action,
        "live_forecast": live_forecast_result,
        "no_retrain": no_retrain,
        "allow_fallback_forecast": allow_fallback_forecast,
    }
    md_path, json_path = write_refresh_summary(result)
    logger.info("Refresh summary written to %s and %s", md_path, json_path)
    return result
