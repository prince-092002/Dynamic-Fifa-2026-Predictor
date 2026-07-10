"""Clean historical matches, 2026 fixtures, and 2026 results."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.cleaning.standardize_team_names import standardize_team_columns
from src.config import PROCESSED_DIR, RAW_KAGGLE_DIR, RAW_MANUAL_DIR
from src.loading.manual_sources import choose_manual_file
from src.logger import get_logger
from src.utils.dates import now_utc_iso, parse_date_series
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    RESULTS_2026_COLUMNS,
    empty_frame,
    read_csv_if_exists,
    save_csv,
)

logger = get_logger(__name__)


HISTORICAL_MATCH_COLUMNS = [
    "date",
    "team_a",
    "team_b",
    "team_a_goals",
    "team_b_goals",
    "tournament",
    "city",
    "country",
    "neutral",
    "winner",
    "is_draw",
    "source",
    "last_updated",
]


def _find_first_csv(directory: Path, preferred_names: list[str]) -> Optional[Path]:
    for name in preferred_names:
        path = directory / name
        if path.exists():
            return path
    files = sorted(directory.glob("*.csv"))
    return files[0] if files else None


def _winner(row: pd.Series) -> object:
    a_goals = pd.to_numeric(row.get("team_a_goals"), errors="coerce")
    b_goals = pd.to_numeric(row.get("team_b_goals"), errors="coerce")
    if pd.isna(a_goals) or pd.isna(b_goals):
        return pd.NA
    if a_goals > b_goals:
        return row.get("team_a")
    if b_goals > a_goals:
        return row.get("team_b")
    return "Draw"


def _clean_match_like(df: pd.DataFrame, source: str) -> pd.DataFrame:
    result = df.copy()
    rename_map = {
        "home_team": "team_a",
        "away_team": "team_b",
        "home_score": "team_a_goals",
        "away_score": "team_b_goals",
        "Date": "date",
        "Home Team Name": "team_a",
        "Away Team Name": "team_b",
        "Home Team Goals": "team_a_goals",
        "Away Team Goals": "team_b_goals",
        "Datetime": "date",
        "Stage": "stage",
        "Stadium": "venue",
    }
    result = result.rename(columns={k: v for k, v in rename_map.items() if k in result.columns})
    for column in HISTORICAL_MATCH_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    result["date"] = parse_date_series(result["date"])
    result["team_a_goals"] = pd.to_numeric(result["team_a_goals"], errors="coerce")
    result["team_b_goals"] = pd.to_numeric(result["team_b_goals"], errors="coerce")
    result = standardize_team_columns(result, ["team_a", "team_b"])
    result["winner"] = result.apply(_winner, axis=1)
    result["is_draw"] = result["winner"].eq("Draw")
    result["source"] = source
    result["last_updated"] = now_utc_iso()
    return result[HISTORICAL_MATCH_COLUMNS]


def clean_historical_international_matches() -> Path:
    input_path = _find_first_csv(
        RAW_KAGGLE_DIR / "international_results",
        ["results.csv", "international_results.csv"],
    )
    output_path = PROCESSED_DIR / "historical_international_matches.csv"
    if not input_path:
        logger.warning("No Kaggle international results CSV found; writing empty output.")
        return save_csv(empty_frame(HISTORICAL_MATCH_COLUMNS), output_path, HISTORICAL_MATCH_COLUMNS)
    df = pd.read_csv(input_path)
    cleaned = _clean_match_like(df, "kaggle_international_results")
    return save_csv(cleaned, output_path, HISTORICAL_MATCH_COLUMNS)


def clean_historical_world_cup_matches() -> Path:
    input_path = _find_first_csv(
        RAW_KAGGLE_DIR / "world_cup_historical",
        ["matches_1930_2022.csv", "WorldCupMatches.csv", "world_cup_matches.csv", "matches.csv"],
    )
    output_path = PROCESSED_DIR / "historical_world_cup_matches.csv"
    if not input_path:
        logger.warning("No historical World Cup CSV found; writing empty output.")
        return save_csv(empty_frame(HISTORICAL_MATCH_COLUMNS), output_path, HISTORICAL_MATCH_COLUMNS)
    df = pd.read_csv(input_path)
    cleaned = _clean_match_like(df, "kaggle_world_cup_historical")
    return save_csv(cleaned, output_path, HISTORICAL_MATCH_COLUMNS)


def _manual_csv(name: str) -> Path:
    kind_by_template = {
        "manual_fixtures_2026_template.csv": ("fixtures", FIXTURES_2026_COLUMNS),
        "manual_results_2026_template.csv": ("results", RESULTS_2026_COLUMNS),
    }
    if name in kind_by_template:
        kind, columns = kind_by_template[name]
        selected, status = choose_manual_file(kind, columns)
        if selected:
            logger.info("Selected manual %s file: %s", kind, selected)
            return selected
        logger.info("No real manual %s rows found (%s); using template path only as schema fallback.", kind, status)
    manual = RAW_MANUAL_DIR / name.replace("_template", "")
    template = RAW_MANUAL_DIR / name
    return manual if manual.exists() else template


def clean_2026_fixtures() -> Path:
    """Build fixtures_2026.csv from manual/API/FIFA/Kaggle data when available."""
    output_path = PROCESSED_DIR / "fixtures_2026.csv"
    candidates = [
        PROCESSED_DIR / "fixtures_2026_api_football.csv",
        PROCESSED_DIR / "fixtures_2026_fifa.csv",
        _manual_csv("manual_fixtures_2026_template.csv"),
        _find_first_csv(RAW_KAGGLE_DIR / "world_cup_2026_schedule", ["matches.csv", "fixtures.csv", "schedule.csv"]),
    ]
    df = empty_frame(FIXTURES_2026_COLUMNS)
    source = "empty"
    for candidate in candidates:
        if candidate and candidate.exists() and candidate.stat().st_size > 0:
            candidate_df = pd.read_csv(candidate)
            if not candidate_df.empty:
                if candidate.name == "matches.csv" and {"home_team_id", "away_team_id"}.issubset(candidate_df.columns):
                    df = _clean_id_based_2026_schedule(candidate.parent, candidate_df)
                else:
                    df = candidate_df
                source = candidate.stem
                break
    df = df.copy()
    rename_map = {
        "home_team": "team_a",
        "away_team": "team_b",
        "match_date": "date",
        "matchday": "date",
        "round": "stage",
        "stadium": "venue",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for column in FIXTURES_2026_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    df["date"] = parse_date_series(df["date"])
    df = standardize_team_columns(df, ["team_a", "team_b"])
    df["status"] = df["status"].fillna("scheduled").astype(str).str.lower()
    df["source"] = df["source"].fillna(source)
    df["last_updated"] = now_utc_iso()
    return save_csv(df, output_path, FIXTURES_2026_COLUMNS)


def _clean_id_based_2026_schedule(folder: Path, matches: pd.DataFrame) -> pd.DataFrame:
    teams_path = folder / "teams.csv"
    cities_path = folder / "host_cities.csv"
    stages_path = folder / "tournament_stages.csv"
    result = matches.copy()
    if teams_path.exists():
        teams = pd.read_csv(teams_path)
        home = teams.rename(columns={"id": "home_team_id", "team_name": "team_a", "group_letter": "home_group"})
        away = teams.rename(columns={"id": "away_team_id", "team_name": "team_b"})
        result = result.merge(home[["home_team_id", "team_a", "home_group"]], on="home_team_id", how="left")
        result = result.merge(away[["away_team_id", "team_b"]], on="away_team_id", how="left")
    if cities_path.exists():
        cities = pd.read_csv(cities_path).rename(
            columns={"id": "city_id", "city_name": "city", "venue_name": "venue"}
        )
        result = result.merge(cities[["city_id", "city", "country", "venue"]], on="city_id", how="left")
    if stages_path.exists():
        stages = pd.read_csv(stages_path).rename(columns={"id": "stage_id", "stage_name": "stage"})
        result = result.merge(stages[["stage_id", "stage"]], on="stage_id", how="left")
    result = result.rename(columns={"id": "match_id", "kickoff_at": "date"})
    result["group"] = result.get("match_label", result.get("home_group", pd.NA))
    result["status"] = "scheduled"
    result["source"] = "kaggle_world_cup_2026_schedule"
    return result


def clean_2026_results() -> Path:
    """Build results_2026.csv from manual/API/FIFA data when available."""
    output_path = PROCESSED_DIR / "results_2026.csv"
    candidates = [
        PROCESSED_DIR / "results_2026_api_football.csv",
        PROCESSED_DIR / "results_2026_fifa.csv",
        _manual_csv("manual_results_2026_template.csv"),
    ]
    df = empty_frame(RESULTS_2026_COLUMNS)
    source = "empty"
    for candidate in candidates:
        if candidate.exists() and candidate.stat().st_size > 0:
            candidate_df = pd.read_csv(candidate)
            if not candidate_df.empty:
                df = candidate_df
                source = candidate.stem
                break
    df = df.copy()
    rename_map = {
        "home_team": "team_a",
        "away_team": "team_b",
        "home_score": "team_a_goals",
        "away_score": "team_b_goals",
        "match_date": "date",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for column in RESULTS_2026_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    df["date"] = parse_date_series(df["date"])
    df["team_a_goals"] = pd.to_numeric(df["team_a_goals"], errors="coerce")
    df["team_b_goals"] = pd.to_numeric(df["team_b_goals"], errors="coerce")
    df = standardize_team_columns(df, ["team_a", "team_b"])
    df["winner"] = df.apply(_winner, axis=1)
    df["is_draw"] = df["winner"].eq("Draw")
    df["status"] = df["status"].fillna("completed").astype(str).str.lower()
    df["source"] = df["source"].fillna(source)
    df["last_updated"] = now_utc_iso()
    return save_csv(df, output_path, RESULTS_2026_COLUMNS)


def run_all_match_cleaners() -> list[Path]:
    return [
        clean_historical_international_matches(),
        clean_historical_world_cup_matches(),
        clean_2026_fixtures(),
        clean_2026_results(),
    ]
