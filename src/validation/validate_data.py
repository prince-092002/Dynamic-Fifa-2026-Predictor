"""Validation checks for processed data outputs."""

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import PROCESSED_DIR, VALIDATION_REPORT_PATH
from src.logger import get_logger
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    MATCHES_MASTER_COLUMNS,
    TEAM_RATINGS_COLUMNS,
    TEAM_STATS_COLUMNS,
    read_csv_if_exists,
)

logger = get_logger(__name__)

VALID_FIXTURE_STATUSES = {"scheduled", "completed", "live", "postponed", "cancelled"}


def _result(dataset: str, check: str, status: str, message: str, rows_affected: int = 0) -> dict:
    return {
        "dataset": dataset,
        "check": check,
        "status": status,
        "message": message,
        "rows_affected": rows_affected,
    }


def _check_required_columns(df: pd.DataFrame, dataset: str, required: Iterable[str]) -> list[dict]:
    missing = [column for column in required if column not in df.columns]
    if missing:
        return [_result(dataset, "required_columns", "fail", f"Missing columns: {', '.join(missing)}", len(missing))]
    return [_result(dataset, "required_columns", "pass", "All required columns are present.")]


def _check_dates(df: pd.DataFrame, dataset: str, date_column: str = "date") -> list[dict]:
    if date_column not in df.columns or df.empty:
        return [_result(dataset, "parseable_dates", "pass", "No dates to validate.")]
    invalid = pd.to_datetime(df[date_column], errors="coerce").isna() & df[date_column].notna()
    status = "fail" if invalid.any() else "pass"
    return [_result(dataset, "parseable_dates", status, f"{int(invalid.sum())} invalid date values.", int(invalid.sum()))]


def _check_numeric(df: pd.DataFrame, dataset: str, columns: Iterable[str]) -> list[dict]:
    results = []
    for column in columns:
        if column not in df.columns or df.empty:
            continue
        invalid = pd.to_numeric(df[column], errors="coerce").isna() & df[column].notna()
        results.append(
            _result(dataset, f"numeric_{column}", "fail" if invalid.any() else "pass", f"{int(invalid.sum())} invalid numeric values.", int(invalid.sum()))
        )
    return results


def _check_non_null_teams(df: pd.DataFrame, dataset: str, columns: Iterable[str]) -> list[dict]:
    results = []
    for column in columns:
        if column not in df.columns or df.empty:
            continue
        missing = df[column].isna() | df[column].astype(str).str.strip().eq("")
        results.append(
            _result(dataset, f"non_null_{column}", "fail" if missing.any() else "pass", f"{int(missing.sum())} missing team names.", int(missing.sum()))
        )
    return results


def _check_duplicate_match_id(df: pd.DataFrame, dataset: str) -> list[dict]:
    if "match_id" not in df.columns or df.empty:
        return []
    ids = df["match_id"].dropna().astype(str).str.strip()
    duplicates = ids[ids.ne("")].duplicated().sum()
    return [_result(dataset, "duplicate_match_id", "fail" if duplicates else "pass", f"{int(duplicates)} duplicate match_id values.", int(duplicates))]


def _count_duplicate_same_day_teams(df: pd.DataFrame) -> int:
    needed = {"date", "team_a", "team_b"}
    if not needed.issubset(df.columns) or df.empty:
        return 0
    pairs = df[["team_a", "team_b"]].fillna("").astype(str).apply(lambda row: "|".join(sorted(row)), axis=1)
    return int(df.assign(pair=pairs).duplicated(subset=["date", "pair"]).sum())


def _check_duplicate_same_day_teams(df: pd.DataFrame, dataset: str) -> list[dict]:
    duplicates = _count_duplicate_same_day_teams(df)
    if duplicates:
        message = (
            f"{duplicates} duplicate same-date team rows in the raw master. Expected condition: the overlapping Kaggle feeds "
            "(international results + world cup historical) list the same matches; feature engineering deduplicates into "
            "matches_master_feature_clean.csv before any feature or model use."
        )
        return [_result(dataset, "duplicate_same_date_same_teams", "warn", message, duplicates)]
    return [_result(dataset, "duplicate_same_date_same_teams", "pass", "0 duplicate same-date team rows.", 0)]


def _check_feature_clean_deduplicated() -> list[dict]:
    dataset = "matches_master_feature_clean"
    clean_path = Path("data/features/intermediate/matches_master_feature_clean.csv")
    if not clean_path.exists():
        return [_result(dataset, "feature_clean_no_duplicates", "warn", "Feature-clean file not built yet; the feature build deduplicates on creation.", 0)]
    clean = pd.read_csv(clean_path, low_memory=False)
    duplicates = _count_duplicate_same_day_teams(clean)
    return [
        _result(
            dataset,
            "feature_clean_no_duplicates",
            "fail" if duplicates else "pass",
            f"{duplicates} duplicate same-date team rows in the deduplicated file consumed by feature engineering.",
            duplicates,
        )
    ]


def _check_fixture_team_names(df: pd.DataFrame, dataset: str) -> list[dict]:
    results = []
    if df.empty:
        return results
    stage = df.get("stage", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    status_series = df.get("status", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    knockout_placeholder_row = ~stage.str.contains("group", na=False) & status_series.ne("completed")
    for column in ["team_a", "team_b"]:
        if column not in df.columns:
            continue
        missing = df[column].isna() | df[column].astype(str).str.strip().eq("")
        hard_missing = int((missing & ~knockout_placeholder_row).sum())
        placeholder_missing = int((missing & knockout_placeholder_row).sum())
        results.append(
            _result(
                dataset,
                f"non_null_{column}",
                "fail" if hard_missing else "pass",
                f"{hard_missing} group-stage or completed fixtures missing team names.",
                hard_missing,
            )
        )
        if placeholder_missing:
            results.append(
                _result(
                    dataset,
                    f"knockout_placeholder_{column}",
                    "warn",
                    f"{placeholder_missing} scheduled knockout fixtures without team names. Expected condition: the pre-tournament template keeps TBD knockout slots; live bracket data resolves them.",
                    placeholder_missing,
                )
            )
    return results


def validate_matches_master() -> list[dict]:
    dataset = "matches_master"
    df = read_csv_if_exists(PROCESSED_DIR / "matches_master.csv", MATCHES_MASTER_COLUMNS)
    results = _check_required_columns(df, dataset, MATCHES_MASTER_COLUMNS)
    results += _check_dates(df, dataset)
    results += _check_numeric(df, dataset, ["team_a_goals", "team_b_goals"])
    results += _check_non_null_teams(df, dataset, ["team_a", "team_b"])
    results += _check_duplicate_match_id(df, dataset)
    results += _check_duplicate_same_day_teams(df, dataset)
    results += _check_feature_clean_deduplicated()
    return results


def validate_fixtures_2026() -> list[dict]:
    dataset = "fixtures_2026"
    df = read_csv_if_exists(PROCESSED_DIR / "fixtures_2026.csv", FIXTURES_2026_COLUMNS)
    results = _check_required_columns(df, dataset, FIXTURES_2026_COLUMNS)
    results += _check_dates(df, dataset)
    results += _check_fixture_team_names(df, dataset)
    results += _check_duplicate_match_id(df, dataset)
    if "status" in df.columns and not df.empty:
        invalid = ~df["status"].dropna().astype(str).str.lower().isin(VALID_FIXTURE_STATUSES)
        results.append(_result(dataset, "valid_status", "fail" if invalid.any() else "pass", f"{int(invalid.sum())} invalid fixture statuses.", int(invalid.sum())))
    return results


def validate_results_2026() -> list[dict]:
    dataset = "results_2026"
    df = read_csv_if_exists(PROCESSED_DIR / "results_2026.csv", [])
    results = _check_dates(df, dataset)
    results += _check_numeric(df, dataset, ["team_a_goals", "team_b_goals"])
    results += _check_non_null_teams(df, dataset, ["team_a", "team_b"])
    if not df.empty and {"team_a_goals", "team_b_goals", "winner"}.issubset(df.columns):
        missing = df[["team_a_goals", "team_b_goals", "winner"]].isna().any(axis=1)
        results.append(_result(dataset, "completed_results_have_scores", "fail" if missing.any() else "pass", f"{int(missing.sum())} rows missing score or winner.", int(missing.sum())))
    return results


def validate_team_ratings() -> list[dict]:
    dataset = "team_ratings"
    df = read_csv_if_exists(PROCESSED_DIR / "team_ratings.csv", TEAM_RATINGS_COLUMNS)
    results = _check_required_columns(df, dataset, TEAM_RATINGS_COLUMNS)
    results += _check_non_null_teams(df, dataset, ["team"])
    results += _check_numeric(df, dataset, ["elo_rating", "elo_rank", "fifa_rank", "fifa_points"])
    return results


def validate_team_stats_2026() -> list[dict]:
    dataset = "team_stats_2026"
    df = read_csv_if_exists(PROCESSED_DIR / "team_stats_2026.csv", TEAM_STATS_COLUMNS)
    results = _check_required_columns(df, dataset, TEAM_STATS_COLUMNS)
    results += _check_non_null_teams(df, dataset, ["team"])
    results += _check_numeric(
        df,
        dataset,
        [
            "matches_played",
            "goals_for",
            "goals_against",
            "goal_difference",
            "xg_for",
            "xg_against",
            "shots",
            "shots_on_target",
            "possession",
            "passes_completed",
            "passes_attempted",
            "yellow_cards",
            "red_cards",
        ],
    )
    return results


def run_all_validations() -> str:
    all_results = []
    for validator in [
        validate_matches_master,
        validate_fixtures_2026,
        validate_results_2026,
        validate_team_ratings,
        validate_team_stats_2026,
    ]:
        all_results.extend(validator())
    report = pd.DataFrame(all_results)
    VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(VALIDATION_REPORT_PATH, index=False)
    failures = report[report["status"].eq("fail")]
    if failures.empty:
        logger.info("Validation completed with no failures.")
    else:
        logger.warning("Validation completed with %s failing checks.", len(failures))
    return str(VALIDATION_REPORT_PATH)

