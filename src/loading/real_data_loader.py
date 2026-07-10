"""Real data loading coordinator with source verification and safe fallbacks."""

from pathlib import Path
from typing import Iterable

from src.cleaning.build_master_dataset import build_matches_master
from src.cleaning.clean_matches import (
    clean_2026_fixtures,
    clean_2026_results,
    clean_historical_international_matches,
    clean_historical_world_cup_matches,
)
from src.cleaning.clean_player_stats import clean_manual_player_stats
from src.cleaning.clean_team_stats import clean_manual_team_ratings, clean_manual_team_stats
from src.config import (
    API_FOOTBALL_KEY,
    KAGGLE_API_TOKEN,
    KAGGLE_KEY,
    KAGGLE_USERNAME,
    PROCESSED_DIR,
    RAW_KAGGLE_DIR,
    ensure_project_directories,
)
from src.fetch.fetch_api_football import (
    diagnose_api_football,
    discover_api_football_world_cup_2026_league,
    fetch_api_football_fixtures_2026,
    fetch_api_football_results_2026,
    fetch_api_football_standings_2026,
    fetch_api_football_team_stats_2026,
    fetch_api_football_teams_2026,
)
from src.fetch.fetch_elo import fetch_world_football_elo
from src.fetch.fetch_fbref import fetch_fbref_world_cup_2026_all_stats
from src.fetch.fetch_kaggle import (
    diagnose_kaggle,
    fetch_international_results,
    fetch_world_cup_2026_schedule,
    fetch_world_cup_historical,
    write_kaggle_file_inventory,
)
from src.loading.data_health import (
    write_data_summary,
    write_feature_readiness_gate,
    write_manual_data_validation,
    write_security_check_report,
)
from src.loading.env_check import check_environment, environment_check_rows, write_env_check_report
from src.loading.manual_sources import choose_manual_file
from src.loading.reports import (
    API_FOOTBALL_STATUS_PATH,
    MANUAL_DATA_NEEDED_PATH,
    PROCESSED_REQUIREMENTS,
    generate_data_readiness_report,
    write_api_football_status,
    write_manual_data_needed_report,
    write_source_status_report,
)
from src.loading.status import source_row
from src.logger import get_logger
from src.update.backup_manager import create_backups_for_processed_files, restore_backup
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    PLAYER_STATS_COLUMNS,
    RESULTS_2026_COLUMNS,
    TEAM_RATINGS_COLUMNS,
    TEAM_STATS_COLUMNS,
    has_real_rows,
    initialize_metadata_files,
)
from src.validation.validate_data import run_all_validations

logger = get_logger(__name__)


def _raw_folder_has_real_csv(folder: Path) -> tuple[bool, str]:
    for path in sorted(folder.glob("*.csv")):
        if has_real_rows(path):
            return True, str(path)
    return False, ""


def _processed_rows(filename: str) -> int:
    path = PROCESSED_DIR / filename
    if not path.exists():
        return 0
    try:
        import pandas as pd

        return len(pd.read_csv(path))
    except Exception:
        return 0


def _csv_rows(path: Path | None) -> int:
    if not path or not path.exists():
        return 0
    try:
        import pandas as pd

        return len(pd.read_csv(path))
    except Exception:
        return 0


def _restore_good_files_if_needed(backup_folder: Path) -> list[str]:
    restored = []
    for filename, required in PROCESSED_REQUIREMENTS.items():
        current_path = PROCESSED_DIR / filename
        backup_path = backup_folder / filename
        if backup_path.exists() and has_real_rows(backup_path, required) and not has_real_rows(current_path, required):
            restore_backup(current_path, backup_path)
            restored.append(str(current_path))
            logger.warning("Restored previous good data for %s from %s", current_path, backup_path)
    return restored


def _manual_status(kind: str, display_name: str, purpose: str, required_columns: Iterable[str]) -> tuple[dict, str | None]:
    path, state = choose_manual_file(kind, required_columns)
    manual_filename = {
        "fixtures": "manual_fixtures_2026.csv",
        "results": "manual_results_2026.csv",
        "team_ratings": "manual_team_ratings.csv",
        "team_stats": "manual_team_stats_2026.csv",
        "player_stats": "manual_player_stats_2026.csv",
    }[kind]
    if path:
        return (
            source_row(
                display_name,
                purpose,
                "no",
                "available",
                rows_fetched=_csv_rows(path),
                raw_output_path=str(path),
                issue="",
                next_action="Run load-real-data to clean this manual fallback.",
            ),
            None,
        )
    return (
        source_row(
            display_name,
            purpose,
            "no",
            "missing",
            issue=state,
            next_action=f"Add real rows to data/raw/manual/{manual_filename}.",
        ),
        display_name,
    )


def _run_kaggle_load(skip_kaggle: bool, prefer: str, manual_needed: list[str]) -> list[dict]:
    rows = []
    kaggle_sources = [
        (
            "Kaggle international results",
            "Historical international training matches",
            RAW_KAGGLE_DIR / "international_results",
            fetch_international_results,
            clean_historical_international_matches,
            "historical_international_matches.csv",
            "Download martj42/international-football-results-from-1872-to-2017 into data/raw/kaggle/international_results/ or add Kaggle credentials.",
        ),
        (
            "Kaggle World Cup historical",
            "Historical World Cup matches",
            RAW_KAGGLE_DIR / "world_cup_historical",
            fetch_world_cup_historical,
            clean_historical_world_cup_matches,
            "historical_world_cup_matches.csv",
            "Download piterfm/fifa-football-world-cup into data/raw/kaggle/world_cup_historical/ or add Kaggle credentials.",
        ),
        (
            "Kaggle 2026 schedule",
            "Unofficial 2026 fixture fallback",
            RAW_KAGGLE_DIR / "world_cup_2026_schedule",
            fetch_world_cup_2026_schedule,
            clean_2026_fixtures,
            "fixtures_2026.csv",
            "Download areezvisram12/fifa-world-cup-2026-match-data-unofficial into data/raw/kaggle/world_cup_2026_schedule/ or use manual fixtures.",
        ),
    ]
    has_creds = bool(KAGGLE_API_TOKEN or (KAGGLE_USERNAME and KAGGLE_KEY))
    for source, purpose, raw_folder, fetcher, cleaner, processed_name, next_action in kaggle_sources:
        if skip_kaggle:
            rows.append(source_row(source, purpose, "yes", "skipped", issue="--skip-kaggle was used", next_action=next_action))
            continue
        raw_has_rows, raw_path = _raw_folder_has_real_csv(raw_folder)
        fetch_result = None
        if prefer != "manual" and has_creds:
            fetch_result = fetcher()
            raw_has_rows, raw_path = _raw_folder_has_real_csv(raw_folder)
        if raw_has_rows:
            output_path = cleaner()
            ready = has_real_rows(PROCESSED_DIR / processed_name, PROCESSED_REQUIREMENTS[processed_name])
            rows.append(
                source_row(
                    source,
                    purpose,
                    "yes",
                    "loaded" if ready else "failed",
                    rows_fetched=_processed_rows(processed_name),
                    raw_output_path=raw_path,
                    processed_output_path=str(output_path),
                    issue="" if ready else "Raw file exists but processed output has no real rows.",
                    next_action="" if ready else "Review source columns and cleaner mappings.",
                )
            )
        else:
            issue = "Kaggle credentials missing and no manually downloaded raw CSV rows found."
            if fetch_result and fetch_result.get("status") == "failed":
                issue = fetch_result.get("error_message", issue)
            rows.append(source_row(source, purpose, "yes", "missing", issue=issue, next_action=next_action))
            manual_needed.append(next_action)
    return rows


def _run_api_football_load(skip_api: bool, prefer: str, manual_needed: list[str]) -> list[dict]:
    purpose = "Live FIFA World Cup 2026 fixtures, results, teams, standings, and stats"
    if skip_api or prefer == "manual":
        message = "API-Football skipped by user preference."
        write_api_football_status("skipped", message)
        return [source_row("API-Football", purpose, "yes", "skipped", issue=message, next_action="Use manual fixtures/results or rerun without skipping API.")]
    if not API_FOOTBALL_KEY:
        message = "API_FOOTBALL_KEY is missing. Add it to .env to fetch live API-Football data."
        write_api_football_status("missing_key", message)
        manual_needed.append("Add API_FOOTBALL_KEY to .env or provide manual fixtures/results CSVs.")
        return [source_row("API-Football", purpose, "yes", "missing", issue=message, next_action="Fill API_FOOTBALL_KEY in .env.")]

    results = [
        fetch_api_football_fixtures_2026(),
        fetch_api_football_results_2026(),
        fetch_api_football_teams_2026(),
        fetch_api_football_standings_2026(),
        fetch_api_football_team_stats_2026(),
    ]
    rows_fetched = sum(int(item.get("rows_fetched", 0) or 0) for item in results)
    issues = "; ".join(item.get("error_message", "") for item in results if item.get("error_message"))
    status = "success" if rows_fetched else "empty"
    if rows_fetched == 0:
        write_api_football_status("empty", issues or "API returned no rows for World Cup 2026.")
    else:
        write_api_football_status("success", f"API-Football returned {rows_fetched} rows.")
    return [
        source_row(
            "API-Football",
            purpose,
            "yes",
            status,
            rows_fetched=rows_fetched,
            raw_output_path="data/raw/api_football/",
            processed_output_path="data/processed/fixtures_2026_api_football.csv; data/processed/results_2026_api_football.csv",
            issue=issues,
            next_action="" if rows_fetched else "Use manual/Kaggle fallback or verify API league/season availability.",
        )
    ]


def _run_elo_load(skip_elo: bool, prefer: str, manual_needed: list[str]) -> list[dict]:
    if skip_elo:
        return [source_row("World Football Elo Ratings", "Current national team Elo ratings", "no", "skipped", issue="--skip-elo was used", next_action="Use manual team ratings or rerun without --skip-elo.")]
    if prefer != "manual":
        result = fetch_world_football_elo()
        if has_real_rows(PROCESSED_DIR / "team_ratings.csv", PROCESSED_REQUIREMENTS["team_ratings.csv"]):
            return [
                source_row(
                    "World Football Elo Ratings",
                    "Current national team Elo ratings",
                    "no",
                    "success",
                    rows_fetched=_processed_rows("team_ratings.csv"),
                    raw_output_path="data/raw/elo/world_football_elo_current.csv",
                    processed_output_path="data/processed/team_ratings.csv",
                )
            ]
        issue = result.get("error_message", "Elo fetch produced no real rows.")
    else:
        issue = "Manual preference selected."

    clean_manual_team_ratings()
    if has_real_rows(PROCESSED_DIR / "team_ratings.csv", PROCESSED_REQUIREMENTS["team_ratings.csv"]):
        return [source_row("Manual team ratings fallback", "Manual team ratings", "no", "loaded", rows_fetched=_processed_rows("team_ratings.csv"), processed_output_path="data/processed/team_ratings.csv")]
    manual_needed.append("Add real team ratings to data/raw/manual/manual_team_ratings.csv.")
    return [source_row("World Football Elo Ratings", "Current national team Elo ratings", "no", "missing", issue=issue, next_action="Add manual team ratings or retry Elo fetch.")]


def _run_fbref_load(skip_fbref: bool, prefer: str, manual_needed: list[str]) -> list[dict]:
    rows = []
    if not skip_fbref and prefer != "manual":
        fetch_fbref_world_cup_2026_all_stats()
    elif skip_fbref:
        rows.append(source_row("FBref team stats", "World Cup team stats", "no", "skipped", issue="--skip-fbref was used", next_action="Use manual team stats or rerun without --skip-fbref."))
        rows.append(source_row("FBref player stats", "World Cup player stats", "no", "skipped", issue="--skip-fbref was used", next_action="Use manual player stats or rerun without --skip-fbref."))

    clean_manual_team_stats()
    clean_manual_player_stats()

    team_ready = has_real_rows(PROCESSED_DIR / "team_stats_2026.csv", PROCESSED_REQUIREMENTS["team_stats_2026.csv"])
    player_ready = has_real_rows(PROCESSED_DIR / "player_stats_2026.csv", PROCESSED_REQUIREMENTS["player_stats_2026.csv"])

    if not any(row["Source"] == "FBref team stats" for row in rows):
        rows.append(source_row("FBref team stats", "World Cup team stats", "no", "loaded" if team_ready else "missing", rows_fetched=_processed_rows("team_stats_2026.csv"), processed_output_path="data/processed/team_stats_2026.csv", issue="" if team_ready else "No FBref/manual team stat rows available.", next_action="" if team_ready else "Add manual team stats or retry FBref later."))
    if not any(row["Source"] == "FBref player stats" for row in rows):
        rows.append(source_row("FBref player stats", "World Cup player stats", "no", "loaded" if player_ready else "missing", rows_fetched=_processed_rows("player_stats_2026.csv"), processed_output_path="data/processed/player_stats_2026.csv", issue="" if player_ready else "No FBref/manual player stat rows available.", next_action="" if player_ready else "Add manual player stats or retry FBref later."))

    if not team_ready:
        manual_needed.append("Add real team stats to data/raw/manual/manual_team_stats_2026.csv.")
    if not player_ready:
        manual_needed.append("Add real player stats to data/raw/manual/manual_player_stats_2026.csv if player-level modeling will be used.")
    return rows


def _manual_fallback_status_rows(manual_needed: list[str]) -> list[dict]:
    checks = [
        ("fixtures", "Manual fixtures fallback", "Manual 2026 fixtures", FIXTURES_2026_COLUMNS),
        ("results", "Manual results fallback", "Manual 2026 results", RESULTS_2026_COLUMNS),
        ("team_ratings", "Manual team ratings fallback", "Manual team ratings", TEAM_RATINGS_COLUMNS),
        ("team_stats", "Manual team stats fallback", "Manual team stats", TEAM_STATS_COLUMNS),
        ("player_stats", "Manual player stats fallback", "Manual player stats", PLAYER_STATS_COLUMNS),
    ]
    rows = []
    for kind, name, purpose, columns in checks:
        row, missing = _manual_status(kind, name, purpose, columns)
        rows.append(row)
        if missing:
            manual_needed.append(f"Provide real rows for {name}.")
    return rows


def load_real_data(
    prefer: str = "api",
    skip_api: bool = False,
    skip_kaggle: bool = False,
    skip_fbref: bool = False,
    skip_elo: bool = False,
    debug: bool = False,
) -> dict:
    """Load real rows when available, falling back to manual files and writing reports."""
    if prefer not in {"api", "manual"}:
        raise ValueError("prefer must be 'api' or 'manual'")

    ensure_project_directories()
    initialize_metadata_files()
    security_report = write_security_check_report()
    env_result = check_environment(create_missing_env=True)
    env_report = write_env_check_report(environment_check_rows(env_result))
    backup_folder = create_backups_for_processed_files()
    logger.info("Real data load started with backup folder %s", backup_folder)

    source_rows = []
    manual_needed = []
    if not skip_api:
        if API_FOOTBALL_KEY:
            diagnose_api_football()
        discover_api_football_world_cup_2026_league()
    if not skip_kaggle and (KAGGLE_API_TOKEN or (KAGGLE_USERNAME and KAGGLE_KEY)):
        diagnose_kaggle()
    source_rows.extend(_run_kaggle_load(skip_kaggle, prefer, manual_needed))
    kaggle_inventory = write_kaggle_file_inventory()
    source_rows.extend(_run_api_football_load(skip_api, prefer, manual_needed))

    # Re-clean fixtures/results after API/Kaggle/manual candidates are available.
    clean_2026_fixtures()
    clean_2026_results()
    restored = _restore_good_files_if_needed(backup_folder)

    source_rows.extend(_run_elo_load(skip_elo, prefer, manual_needed))
    source_rows.extend(_run_fbref_load(skip_fbref, prefer, manual_needed))
    source_rows.extend(_manual_fallback_status_rows(manual_needed))
    restored.extend(_restore_good_files_if_needed(backup_folder))

    build_matches_master()
    validation_report = run_all_validations()
    restored.extend(_restore_good_files_if_needed(backup_folder))

    manual_validation_report = write_manual_data_validation()
    data_summary = write_data_summary()
    readiness_gate = write_feature_readiness_gate()
    source_status_report = write_source_status_report(source_rows)
    manual_report = write_manual_data_needed_report(manual_needed)
    readiness_report = generate_data_readiness_report(source_rows)

    return {
        "env_created": env_result.get("created_env", False),
        "security_check_report": security_report,
        "env_check_report": env_report,
        "backup_folder": str(backup_folder),
        "source_status_report": source_status_report,
        "manual_data_needed_report": manual_report,
        "api_football_status_report": str(API_FOOTBALL_STATUS_PATH),
        "data_readiness_report": readiness_report,
        "validation_report": validation_report,
        "manual_data_validation_report": manual_validation_report,
        "kaggle_file_inventory": kaggle_inventory,
        "data_summary_report": data_summary["md"],
        "feature_readiness_gate": readiness_gate["report"],
        "restored_files": restored,
        "source_rows": source_rows,
    }
