"""Clean team rating and team-stat fallback files."""

import pandas as pd

from src.cleaning.standardize_team_names import standardize_team_columns
from src.config import PROCESSED_DIR, RAW_MANUAL_DIR
from src.loading.manual_sources import choose_manual_file
from src.utils.dates import now_utc_iso
from src.utils.files import TEAM_RATINGS_COLUMNS, TEAM_STATS_COLUMNS, empty_frame, read_csv_if_exists, save_csv


def clean_manual_team_ratings() -> str:
    output = PROCESSED_DIR / "team_ratings.csv"
    existing = read_csv_if_exists(output, TEAM_RATINGS_COLUMNS)
    if not existing.empty:
        return str(output)
    input_path, _ = choose_manual_file("team_ratings", TEAM_RATINGS_COLUMNS)
    if input_path is None:
        input_path = RAW_MANUAL_DIR / "manual_team_ratings_template.csv"
    df = pd.read_csv(input_path) if input_path.exists() else empty_frame(TEAM_RATINGS_COLUMNS)
    for column in TEAM_RATINGS_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    df = standardize_team_columns(df, ["team"])
    df["last_updated"] = df["last_updated"].fillna(now_utc_iso())
    save_csv(df, output, TEAM_RATINGS_COLUMNS)
    return str(output)


def clean_manual_team_stats() -> str:
    output = PROCESSED_DIR / "team_stats_2026.csv"
    existing = read_csv_if_exists(output, TEAM_STATS_COLUMNS)
    if not existing.empty:
        return str(output)
    input_path, _ = choose_manual_file("team_stats", TEAM_STATS_COLUMNS)
    if input_path is None:
        input_path = RAW_MANUAL_DIR / "manual_team_stats_2026_template.csv"
    df = pd.read_csv(input_path) if input_path.exists() else empty_frame(TEAM_STATS_COLUMNS)
    for column in TEAM_STATS_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    df = standardize_team_columns(df, ["team"])
    df["last_updated"] = df["last_updated"].fillna(now_utc_iso())
    save_csv(df, output, TEAM_STATS_COLUMNS)
    return str(output)
