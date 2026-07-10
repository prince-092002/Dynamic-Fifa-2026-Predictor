"""Build the unified matches_master.csv dataset."""

import pandas as pd

from src.cleaning.clean_matches import _winner
from src.cleaning.standardize_team_names import standardize_team_columns
from src.config import PROCESSED_DIR
from src.logger import get_logger
from src.utils.dates import now_utc_iso, parse_date_series
from src.utils.files import MATCHES_MASTER_COLUMNS, empty_frame, read_csv_if_exists, save_csv

logger = get_logger(__name__)


def _to_master(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    result = df.copy()
    for column in MATCHES_MASTER_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    result["date"] = parse_date_series(result["date"])
    result["team_a_goals"] = pd.to_numeric(result["team_a_goals"], errors="coerce")
    result["team_b_goals"] = pd.to_numeric(result["team_b_goals"], errors="coerce")
    result = standardize_team_columns(result, ["team_a", "team_b"])
    result["winner"] = result.apply(_winner, axis=1)
    result["is_draw"] = result["winner"].eq("Draw")
    result["source"] = result["source"].fillna(source_name)
    result["last_updated"] = result["last_updated"].fillna(now_utc_iso())
    return result[MATCHES_MASTER_COLUMNS]


def build_matches_master() -> str:
    """Combine historical matches and completed 2026 results into one CSV."""
    inputs = [
        (PROCESSED_DIR / "historical_international_matches.csv", "historical_international"),
        (PROCESSED_DIR / "historical_world_cup_matches.csv", "historical_world_cup"),
        (PROCESSED_DIR / "results_2026.csv", "world_cup_2026_results"),
    ]
    frames = []
    for path, source in inputs:
        df = read_csv_if_exists(path, MATCHES_MASTER_COLUMNS)
        if not df.empty:
            frames.append(_to_master(df, source))

    master = pd.concat(frames, ignore_index=True) if frames else empty_frame(MATCHES_MASTER_COLUMNS)
    if not master.empty:
        missing_ids = master["match_id"].isna() | master["match_id"].astype(str).str.strip().eq("")
        master.loc[missing_ids, "match_id"] = (
            master.loc[missing_ids, ["date", "team_a", "team_b", "tournament"]]
            .fillna("")
            .astype(str)
            .agg("|".join, axis=1)
            .str.lower()
            .str.replace(r"[^a-z0-9]+", "-", regex=True)
            .str.strip("-")
        )
        master = master.drop_duplicates(subset=["date", "team_a", "team_b", "tournament"], keep="last")
    output = PROCESSED_DIR / "matches_master.csv"
    save_csv(master, output, MATCHES_MASTER_COLUMNS)
    logger.info("Saved matches master with %s rows to %s", len(master), output)
    return str(output)

