"""Fetch World Football Elo ratings."""

from datetime import date

import pandas as pd

from src.cleaning.standardize_team_names import standardize_team_columns
from src.config import PROCESSED_DIR, RAW_ELO_DIR, REPORTS_DIR, RAW_KAGGLE_DIR, RAW_MANUAL_DIR
from src.logger import get_logger
from src.utils.dates import now_utc_iso
from src.utils.files import TEAM_RATINGS_COLUMNS, append_fetch_log, empty_frame, has_real_rows, save_csv

logger = get_logger(__name__)


ELO_URL = "https://eloratings.net/"


def _normalize_elo_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [str(column).strip().lower().replace(" ", "_") for column in result.columns]
    rename_map = {
        "rank": "elo_rank",
        "#": "elo_rank",
        "team": "team",
        "country": "team",
        "rating": "elo_rating",
        "elo": "elo_rating",
    }
    result = result.rename(columns={k: v for k, v in rename_map.items() if k in result.columns})
    if "team" not in result.columns:
        text_cols = [column for column in result.columns if result[column].dtype == object]
        if text_cols:
            result["team"] = result[text_cols[0]]
    if "elo_rating" not in result.columns:
        numeric_cols = [column for column in result.columns if pd.api.types.is_numeric_dtype(result[column])]
        if numeric_cols:
            result["elo_rating"] = result[numeric_cols[-1]]
    if "elo_rank" not in result.columns:
        result["elo_rank"] = range(1, len(result) + 1)
    for column in TEAM_RATINGS_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    result = standardize_team_columns(result, ["team"])
    result["elo_rating"] = pd.to_numeric(result["elo_rating"], errors="coerce")
    result["elo_rank"] = pd.to_numeric(result["elo_rank"], errors="coerce")
    result["rating_date"] = str(date.today())
    result["source"] = "world_football_elo"
    result["last_updated"] = now_utc_iso()
    return result[TEAM_RATINGS_COLUMNS].dropna(subset=["team"])


def fetch_world_football_elo() -> dict:
    raw_output = RAW_ELO_DIR / "world_football_elo_current.csv"
    processed_output = PROCESSED_DIR / "team_ratings.csv"
    try:
        tables = pd.read_html(ELO_URL)
        if not tables:
            raise ValueError("No tables found at World Football Elo page.")
        best_table = max(tables, key=len)
        raw_output.parent.mkdir(parents=True, exist_ok=True)
        best_table.to_csv(raw_output, index=False)
        cleaned = _normalize_elo_table(best_table)
        save_csv(cleaned, processed_output, TEAM_RATINGS_COLUMNS)
        append_fetch_log(
            source="world_football_elo",
            source_url=ELO_URL,
            status="success",
            rows_fetched=len(cleaned),
            raw_output_path=str(raw_output),
            processed_output_path=str(processed_output),
        )
        _write_elo_status("success", f"Loaded {len(cleaned)} Elo rows from pandas.read_html.", str(raw_output), str(processed_output))
        return {
            "source": "world_football_elo",
            "status": "success",
            "rows_fetched": len(cleaned),
            "output_file": str(processed_output),
            "error_message": "",
        }
    except Exception as exc:
        logger.exception("Could not fetch World Football Elo ratings")
        kaggle_ratings = _load_kaggle_fifa_ranking_fallback()
        if not kaggle_ratings.empty:
            save_csv(kaggle_ratings, processed_output, TEAM_RATINGS_COLUMNS)
            rows = len(kaggle_ratings)
            _write_elo_status("kaggle_fifa_ranking_fallback", f"Web parse failed; loaded {rows} FIFA ranking rows from Kaggle fallback. Error: {exc}", "data/raw/kaggle/world_cup_historical/fifa_ranking_*.csv", str(processed_output))
            return {"source": "world_football_elo", "status": "kaggle_fifa_ranking_fallback", "rows_fetched": rows, "output_file": str(processed_output), "error_message": str(exc)}
        manual = RAW_MANUAL_DIR / "manual_team_ratings.csv"
        if has_real_rows(manual, TEAM_RATINGS_COLUMNS):
            manual_df = pd.read_csv(manual)
            save_csv(manual_df, processed_output, TEAM_RATINGS_COLUMNS)
            rows = len(manual_df)
            _write_elo_status("manual_fallback", f"Web parse failed; loaded {rows} manual rows. Error: {exc}", str(manual), str(processed_output))
            return {"source": "world_football_elo", "status": "manual_fallback", "rows_fetched": rows, "output_file": str(processed_output), "error_message": str(exc)}
        if not has_real_rows(processed_output, TEAM_RATINGS_COLUMNS):
            save_csv(empty_frame(TEAM_RATINGS_COLUMNS), processed_output, TEAM_RATINGS_COLUMNS)
        append_fetch_log(
            source="world_football_elo",
            source_url=ELO_URL,
            status="failed",
            raw_output_path=str(raw_output),
            processed_output_path=str(processed_output),
            notes=str(exc),
        )
        _write_elo_status("failed", f"Website could not be parsed and no manual fallback rows were available. Error: {exc}", str(raw_output), str(processed_output))
        return {
            "source": "world_football_elo",
            "status": "failed",
            "rows_fetched": 0,
            "output_file": str(processed_output),
            "error_message": str(exc),
        }


def _load_kaggle_fifa_ranking_fallback() -> pd.DataFrame:
    ranking_files = sorted((RAW_KAGGLE_DIR / "world_cup_historical").glob("fifa_ranking_*.csv"))
    if not ranking_files:
        return empty_frame(TEAM_RATINGS_COLUMNS)
    latest = ranking_files[-1]
    try:
        df = pd.read_csv(latest)
    except Exception:
        return empty_frame(TEAM_RATINGS_COLUMNS)
    result = pd.DataFrame()
    result["team"] = df.get("team", pd.Series(dtype=object))
    result["fifa_rank"] = pd.to_numeric(df.get("rank"), errors="coerce")
    result["fifa_points"] = pd.to_numeric(df.get("points"), errors="coerce")
    result["elo_rank"] = pd.NA
    result["elo_rating"] = pd.NA
    result["rating_date"] = latest.stem.replace("fifa_ranking_", "")
    result["source"] = "kaggle_fifa_ranking"
    result["last_updated"] = now_utc_iso()
    result = standardize_team_columns(result, ["team"])
    return result[TEAM_RATINGS_COLUMNS].dropna(subset=["team"])


def _write_elo_status(status: str, message: str, raw_output: str, processed_output: str) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Elo Loading Status",
        "",
        f"- Status: {status}",
        f"- Message: {message}",
        f"- Raw/manual input: {raw_output or 'none'}",
        f"- Processed output: {processed_output}",
        "",
        "If web parsing still fails, add rows to `data/raw/manual/manual_team_ratings.csv` and rerun `python main.py load-real-data`.",
    ]
    path = REPORTS_DIR / "elo_loading_status.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
