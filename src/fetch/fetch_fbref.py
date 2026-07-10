"""FBref World Cup stat fetcher."""

from io import StringIO
import time

from bs4 import BeautifulSoup, Comment
import pandas as pd

from src.cleaning.standardize_team_names import standardize_team_columns
from src.config import PROCESSED_DIR, RAW_FBREF_DIR
from src.logger import get_logger
from src.utils.dates import now_utc_iso
from src.utils.files import PLAYER_STATS_COLUMNS, TEAM_STATS_COLUMNS, append_fetch_log, empty_frame, save_csv
from src.utils.http import get_text

logger = get_logger(__name__)

FBREF_URLS = {
    "summary": "https://fbref.com/en/comps/1/World-Cup-Stats",
    "standard": "https://fbref.com/en/comps/1/stats/World-Cup-Stats",
    "shooting": "https://fbref.com/en/comps/1/shooting/World-Cup-Stats",
    "passing": "https://fbref.com/en/comps/1/passing/World-Cup-Stats",
    "defense": "https://fbref.com/en/comps/1/defense/World-Cup-Stats",
    "possession": "https://fbref.com/en/comps/1/possession/World-Cup-Stats",
    "keepers": "https://fbref.com/en/comps/1/keepers/World-Cup-Stats",
    "misc": "https://fbref.com/en/comps/1/misc/World-Cup-Stats",
}


def _extract_tables_from_fbref_html(html: str) -> list[pd.DataFrame]:
    tables = pd.read_html(StringIO(html))
    soup = BeautifulSoup(html, "html.parser")
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if "<table" not in comment:
            continue
        try:
            tables.extend(pd.read_html(StringIO(str(comment))))
        except ValueError:
            continue
    return tables


def fetch_fbref_table(url: str, output_path) -> dict:
    """Fetch one FBref page and save every parseable table as CSV."""
    try:
        html = get_text(url, timeout=30)
        tables = _extract_tables_from_fbref_html(html)
        if not tables:
            raise ValueError("No tables found in FBref page.")
        output_path = RAW_FBREF_DIR / output_path if isinstance(output_path, str) else output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        saved = []
        for idx, table in enumerate(tables):
            table.columns = ["_".join([str(part) for part in column if str(part) != "nan"]) if isinstance(column, tuple) else str(column) for column in table.columns]
            table_path = output_path.with_name(f"{output_path.stem}_{idx}.csv")
            table.to_csv(table_path, index=False)
            saved.append(table_path)
        append_fetch_log("fbref", url, "success", sum(len(table) for table in tables), raw_output_path="; ".join(map(str, saved)))
        return {"source": "fbref", "status": "success", "rows_fetched": sum(len(table) for table in tables), "output_file": str(saved[0]), "error_message": ""}
    except Exception as exc:
        warning_path = RAW_FBREF_DIR / "fbref_fetch_warning.txt"
        warning_path.write_text(
            "FBref could not be fetched or parsed. It may be blocking automated requests. "
            "Use manual CSVs in data/raw/manual as a fallback.\n"
            f"Original error: {exc}\n",
            encoding="utf-8",
        )
        logger.warning("FBref fetch failed for %s: %s", url, exc)
        append_fetch_log("fbref", url, "skipped", raw_output_path=str(warning_path), notes=str(exc))
        return {"source": "fbref", "status": "skipped", "rows_fetched": 0, "output_file": str(warning_path), "error_message": str(exc)}


def fetch_fbref_world_cup_2026_all_stats() -> list[dict]:
    results = []
    for name, url in FBREF_URLS.items():
        results.append(fetch_fbref_table(url, RAW_FBREF_DIR / f"fbref_{name}.csv"))
        time.sleep(3)
    clean_fbref_team_stats()
    clean_fbref_player_stats()
    return results


def _read_all_raw_fbref() -> list[pd.DataFrame]:
    frames = []
    for path in sorted(RAW_FBREF_DIR.glob("fbref_*_*.csv")):
        try:
            frames.append(pd.read_csv(path))
        except Exception:
            logger.warning("Could not read FBref raw table %s", path)
    return frames


def clean_fbref_team_stats() -> str:
    frames = _read_all_raw_fbref()
    output = PROCESSED_DIR / "team_stats_2026.csv"
    if not frames:
        save_csv(empty_frame(TEAM_STATS_COLUMNS), output, TEAM_STATS_COLUMNS)
        return str(output)
    candidate = max(frames, key=len).copy()
    candidate.columns = [str(column).lower().replace(" ", "_") for column in candidate.columns]
    rename = {
        "squad": "team",
        "team": "team",
        "mp": "matches_played",
        "playing_time_mp": "matches_played",
        "performance_gls": "goals_for",
        "gls": "goals_for",
        "expected_xg": "xg_for",
        "xg": "xg_for",
        "standard_sh": "shots",
        "sh": "shots",
        "standard_sot": "shots_on_target",
        "sot": "shots_on_target",
        "poss": "possession",
        "performance_crdy": "yellow_cards",
        "performance_crdr": "red_cards",
    }
    candidate = candidate.rename(columns={k: v for k, v in rename.items() if k in candidate.columns})
    for column in TEAM_STATS_COLUMNS:
        if column not in candidate.columns:
            candidate[column] = pd.NA
    candidate = standardize_team_columns(candidate, ["team"])
    candidate["source"] = "fbref"
    candidate["last_updated"] = now_utc_iso()
    save_csv(candidate, output, TEAM_STATS_COLUMNS)
    return str(output)


def clean_fbref_player_stats() -> str:
    frames = _read_all_raw_fbref()
    output = PROCESSED_DIR / "player_stats_2026.csv"
    if not frames:
        save_csv(empty_frame(PLAYER_STATS_COLUMNS), output, PLAYER_STATS_COLUMNS)
        return str(output)
    candidate = max(frames, key=len).copy()
    candidate.columns = [str(column).lower().replace(" ", "_") for column in candidate.columns]
    rename = {
        "player": "player",
        "nation": "team",
        "squad": "team",
        "pos": "position",
        "age": "age",
        "playing_time_min": "minutes",
        "min": "minutes",
        "performance_gls": "goals",
        "gls": "goals",
        "performance_ast": "assists",
        "ast": "assists",
        "expected_xg": "xg",
        "xg": "xg",
        "standard_sh": "shots",
        "sh": "shots",
        "standard_sot": "shots_on_target",
        "sot": "shots_on_target",
        "performance_crdy": "yellow_cards",
        "performance_crdr": "red_cards",
    }
    candidate = candidate.rename(columns={k: v for k, v in rename.items() if k in candidate.columns})
    for column in PLAYER_STATS_COLUMNS:
        if column not in candidate.columns:
            candidate[column] = pd.NA
    candidate = standardize_team_columns(candidate, ["team"])
    candidate["source"] = "fbref"
    candidate["last_updated"] = now_utc_iso()
    save_csv(candidate, output, PLAYER_STATS_COLUMNS)
    return str(output)

