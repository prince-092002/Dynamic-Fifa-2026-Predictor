"""Run all data fetchers with fault isolation."""

import pandas as pd

from src.config import ensure_project_directories
from src.fetch.fetch_api_football import (
    fetch_api_football_fixtures_2026,
    fetch_api_football_results_2026,
    fetch_api_football_standings_2026,
    fetch_api_football_team_stats_2026,
    fetch_api_football_teams_2026,
)
from src.fetch.fetch_elo import fetch_world_football_elo
from src.fetch.fetch_fbref import fetch_fbref_world_cup_2026_all_stats
from src.fetch.fetch_fifa import clean_fifa_matches, fetch_fifa_data_centre_matches
from src.fetch.fetch_kaggle import (
    fetch_international_results,
    fetch_world_cup_2026_schedule,
    fetch_world_cup_historical,
)
from src.logger import get_logger
from src.utils.files import initialize_metadata_files

logger = get_logger(__name__)


def _safe_call(name: str, func):
    try:
        return func()
    except Exception as exc:
        logger.exception("%s failed unexpectedly", name)
        return {"source": name, "status": "failed", "rows_fetched": 0, "output_file": "", "error_message": str(exc)}


def fetch_all_sources() -> pd.DataFrame:
    ensure_project_directories()
    initialize_metadata_files()
    results = []
    for name, func in [
        ("fifa_data_centre", fetch_fifa_data_centre_matches),
        ("fifa_clean", clean_fifa_matches),
        ("api_football_fixtures", fetch_api_football_fixtures_2026),
        ("api_football_results", fetch_api_football_results_2026),
        ("api_football_teams", fetch_api_football_teams_2026),
        ("api_football_standings", fetch_api_football_standings_2026),
        ("api_football_team_stats", fetch_api_football_team_stats_2026),
        ("kaggle_international_results", fetch_international_results),
        ("kaggle_world_cup_historical", fetch_world_cup_historical),
        ("kaggle_world_cup_2026_schedule", fetch_world_cup_2026_schedule),
        ("world_football_elo", fetch_world_football_elo),
    ]:
        results.append(_safe_call(name, func))
    fbref_results = _safe_call("fbref", fetch_fbref_world_cup_2026_all_stats)
    if isinstance(fbref_results, list):
        results.extend(fbref_results)
    else:
        results.append(fbref_results)
    summary = pd.DataFrame(results)
    print(summary[["source", "status", "rows_fetched", "output_file", "error_message"]].to_string(index=False))
    return summary

