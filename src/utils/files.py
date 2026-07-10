"""Filesystem and CSV helpers."""

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from src.config import (
    DATA_SOURCES_PATH,
    FETCH_LOG_PATH,
    RAW_MANUAL_DIR,
    ensure_project_directories,
)
from src.utils.dates import now_utc_iso


MATCHES_MASTER_COLUMNS = [
    "match_id",
    "date",
    "team_a",
    "team_b",
    "team_a_goals",
    "team_b_goals",
    "winner",
    "is_draw",
    "tournament",
    "stage",
    "city",
    "country",
    "venue",
    "neutral",
    "source",
    "last_updated",
]

FIXTURES_2026_COLUMNS = [
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
    "source",
    "last_updated",
]

RESULTS_2026_COLUMNS = [
    "match_id",
    "date",
    "stage",
    "team_a",
    "team_b",
    "team_a_goals",
    "team_b_goals",
    "winner",
    "is_draw",
    "status",
    "source",
    "last_updated",
]

TEAM_RATINGS_COLUMNS = [
    "team",
    "fifa_rank",
    "fifa_points",
    "elo_rank",
    "elo_rating",
    "rating_date",
    "source",
    "last_updated",
]

TEAM_STATS_COLUMNS = [
    "team",
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
    "source",
    "last_updated",
]

PLAYER_STATS_COLUMNS = [
    "player",
    "team",
    "position",
    "age",
    "minutes",
    "goals",
    "assists",
    "xg",
    "shots",
    "shots_on_target",
    "passes_completed",
    "yellow_cards",
    "red_cards",
    "source",
    "last_updated",
]

TEAM_NAME_MAP_COLUMNS = ["raw_team_name", "standard_team_name", "source"]
FETCH_LOG_COLUMNS = [
    "timestamp",
    "source",
    "source_url",
    "status",
    "rows_fetched",
    "raw_output_path",
    "processed_output_path",
    "notes",
]


def empty_frame(columns: Iterable[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=list(columns))


def read_csv_if_exists(path: Path, columns: Optional[Iterable[str]] = None) -> pd.DataFrame:
    if path.exists() and path.stat().st_size > 0:
        return pd.read_csv(path)
    return empty_frame(columns or [])


def has_real_rows(file_path: Path, required_columns: Optional[Iterable[str]] = None) -> bool:
    """Return True when a CSV exists, has required columns, and has at least one useful row."""
    file_path = Path(file_path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        return False
    try:
        df = pd.read_csv(file_path)
    except Exception:
        return False
    if df.empty:
        return False
    if required_columns:
        required_columns = list(required_columns)
        missing = [column for column in required_columns if column not in df.columns]
        if missing:
            return False
        metadata_columns = {"source", "last_updated", "is_draw", "neutral"}
        critical_columns = [column for column in required_columns if column not in metadata_columns]
    else:
        critical_columns = list(df.columns)
    critical_frame = df[[column for column in critical_columns if column in df.columns]]
    if critical_frame.empty:
        return False
    return critical_frame.notna().any(axis=1).any()


def save_csv(df: pd.DataFrame, path: Path, columns: Optional[Iterable[str]] = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is not None:
        for column in columns:
            if column not in df.columns:
                df[column] = pd.NA
        df = df[list(columns)]
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    df.to_csv(temp_path, index=False)
    temp_path.replace(path)
    return path


def append_fetch_log(
    source: str,
    source_url: str,
    status: str,
    rows_fetched: int = 0,
    raw_output_path: str = "",
    processed_output_path: str = "",
    notes: str = "",
) -> None:
    ensure_project_directories()
    row = {
        "timestamp": now_utc_iso(),
        "source": source,
        "source_url": source_url,
        "status": status,
        "rows_fetched": rows_fetched,
        "raw_output_path": raw_output_path,
        "processed_output_path": processed_output_path,
        "notes": notes,
    }
    existing = read_csv_if_exists(FETCH_LOG_PATH, FETCH_LOG_COLUMNS)
    save_csv(pd.concat([existing, pd.DataFrame([row])], ignore_index=True), FETCH_LOG_PATH, FETCH_LOG_COLUMNS)


def initialize_metadata_files() -> None:
    """Create metadata files and manual templates if they do not exist."""
    ensure_project_directories()
    if not FETCH_LOG_PATH.exists():
        save_csv(empty_frame(FETCH_LOG_COLUMNS), FETCH_LOG_PATH, FETCH_LOG_COLUMNS)

    data_sources = pd.DataFrame(
        [
            {
                "source_name": "FIFA Data Centre",
                "source_type": "website",
                "url": "https://inside.fifa.com/data-centre/matches",
                "usage": "Official fixtures, results, teams, venues",
                "requires_api_key": "no",
                "official_or_unofficial": "official",
                "notes": "May be JavaScript-rendered; use manual/API fallback if blocked.",
            },
            {
                "source_name": "API-Football",
                "source_type": "api",
                "url": "https://www.api-football.com/",
                "usage": "Live fixtures, results, teams, standings, stats",
                "requires_api_key": "yes",
                "official_or_unofficial": "third-party",
                "notes": "Requires API_FOOTBALL_KEY in .env.",
            },
            {
                "source_name": "Kaggle international football results",
                "source_type": "downloadable dataset",
                "url": "https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017",
                "usage": "Historical international match training data",
                "requires_api_key": "yes",
                "official_or_unofficial": "unofficial",
                "notes": "Requires Kaggle credentials or manual download.",
            },
            {
                "source_name": "Kaggle FIFA World Cup historical",
                "source_type": "downloadable dataset",
                "url": "https://www.kaggle.com/datasets/piterfm/fifa-football-world-cup",
                "usage": "Historical World Cup match data",
                "requires_api_key": "yes",
                "official_or_unofficial": "unofficial",
                "notes": "Useful for World Cup-specific patterns.",
            },
            {
                "source_name": "Kaggle FIFA World Cup 2026 unofficial schedule",
                "source_type": "downloadable dataset",
                "url": "https://www.kaggle.com/datasets/areezvisram12/fifa-world-cup-2026-match-data-unofficial",
                "usage": "Backup 2026 schedule, venues, stages",
                "requires_api_key": "yes",
                "official_or_unofficial": "unofficial",
                "notes": "May differ from official FIFA data.",
            },
            {
                "source_name": "World Football Elo Ratings",
                "source_type": "website",
                "url": "https://eloratings.net/",
                "usage": "Current national team Elo ratings",
                "requires_api_key": "no",
                "official_or_unofficial": "third-party",
                "notes": "Parsed politely with pandas.read_html.",
            },
            {
                "source_name": "FBref World Cup stats",
                "source_type": "website",
                "url": "https://fbref.com/en/comps/1/World-Cup-Stats",
                "usage": "Team and player tournament stats",
                "requires_api_key": "no",
                "official_or_unofficial": "third-party",
                "notes": "May block automated requests; manual CSV fallback is supported.",
            },
        ]
    )
    save_csv(data_sources, DATA_SOURCES_PATH)

    templates = {
        "manual_fixtures_2026_template.csv": FIXTURES_2026_COLUMNS,
        "manual_results_2026_template.csv": RESULTS_2026_COLUMNS,
        "manual_team_ratings_template.csv": TEAM_RATINGS_COLUMNS,
        "manual_team_stats_2026_template.csv": TEAM_STATS_COLUMNS,
        "manual_player_stats_2026_template.csv": PLAYER_STATS_COLUMNS,
    }
    for filename, columns in templates.items():
        path = RAW_MANUAL_DIR / filename
        if not path.exists():
            save_csv(empty_frame(columns), path, columns)
