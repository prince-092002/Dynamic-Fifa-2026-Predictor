"""Manual CSV fallback discovery and loading helpers."""

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import RAW_MANUAL_DIR
from src.logger import get_logger
from src.utils.files import has_real_rows, read_csv_if_exists

logger = get_logger(__name__)


MANUAL_FILES = {
    "fixtures": ("manual_fixtures_2026.csv", "manual_fixtures_2026_template.csv"),
    "results": ("manual_results_2026.csv", "manual_results_2026_template.csv"),
    "team_ratings": ("manual_team_ratings.csv", "manual_team_ratings_template.csv"),
    "team_stats": ("manual_team_stats_2026.csv", "manual_team_stats_2026_template.csv"),
    "player_stats": ("manual_player_stats_2026.csv", "manual_player_stats_2026_template.csv"),
}


def choose_manual_file(kind: str, required_columns: Iterable[str] | None = None) -> tuple[Path | None, str]:
    """Choose the best manual CSV, preferring non-template files with real rows."""
    final_name, template_name = MANUAL_FILES[kind]
    final_path = RAW_MANUAL_DIR / final_name
    template_path = RAW_MANUAL_DIR / template_name

    if has_real_rows(final_path, required_columns):
        logger.info("Using manual %s data from %s", kind, final_path)
        return final_path, "using_non_template_manual_file"
    if final_path.exists():
        logger.info("Manual %s file exists but has no real rows: %s", kind, final_path)

    if has_real_rows(template_path, required_columns):
        logger.info("Using manual %s data from template file %s", kind, template_path)
        return template_path, "using_template_manual_file"
    if template_path.exists():
        logger.info("Manual %s template exists but has no real rows: %s", kind, template_path)

    return None, "no_real_manual_rows"


def read_manual_file(kind: str, required_columns: Iterable[str] | None = None) -> tuple[pd.DataFrame, Path | None, str]:
    path, status = choose_manual_file(kind, required_columns)
    if not path:
        return pd.DataFrame(columns=list(required_columns or [])), None, status
    return read_csv_if_exists(path, required_columns), path, status

