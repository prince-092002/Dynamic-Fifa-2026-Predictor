"""Team-name standardization utilities."""

from pathlib import Path
import re
import unicodedata

import pandas as pd

from src.config import PROCESSED_DIR, UNMAPPED_TEAMS_PATH
from src.logger import get_logger
from src.utils.files import TEAM_NAME_MAP_COLUMNS, save_csv

logger = get_logger(__name__)


DEFAULT_TEAM_MAPPINGS = {
    "USA": "United States",
    "U.S.A.": "United States",
    "United States of America": "United States",
    "USMNT": "United States",
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "South Korea": "South Korea",
    "IR Iran": "Iran",
    "Iran (Islamic Republic of)": "Iran",
    "Cote d'Ivoire": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "CÃ´te d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Czechia": "Czech Republic",
    "Czech Republic": "Czech Republic",
    "Türkiye": "Turkey",
    "TÃ¼rkiye": "Turkey",
    "Turkiye": "Turkey",
    "England": "England",
    "Wales": "Wales",
    "Scotland": "Scotland",
    "Northern Ireland": "Northern Ireland",
}


def _ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")


def basic_clean_team_name(name: object) -> object:
    """Clean spacing and casing while preserving common acronyms."""
    if pd.isna(name):
        return pd.NA
    text = str(name).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return pd.NA
    if text.upper() in {"USA", "USMNT"}:
        return text.upper()
    return text.title() if text.isupper() else text


def load_team_name_map(path: Path | None = None) -> dict[str, str]:
    """Load user mappings and merge them with built-in examples."""
    map_path = path or PROCESSED_DIR / "team_name_map.csv"
    mappings = dict(DEFAULT_TEAM_MAPPINGS)
    if map_path.exists() and map_path.stat().st_size > 0:
        df = pd.read_csv(map_path)
        for _, row in df.dropna(subset=["raw_team_name", "standard_team_name"]).iterrows():
            mappings[str(row["raw_team_name"]).strip()] = str(row["standard_team_name"]).strip()
    folded = {_ascii_fold(k).lower(): v for k, v in mappings.items()}
    mappings.update(folded)
    return mappings


def standardize_team_name(name: object, mappings: dict[str, str] | None = None) -> object:
    """Convert a raw team name into the project's canonical form."""
    cleaned = basic_clean_team_name(name)
    if pd.isna(cleaned):
        return pd.NA
    mappings = mappings or load_team_name_map()
    candidates = [
        str(cleaned),
        _ascii_fold(str(cleaned)),
        _ascii_fold(str(cleaned)).lower(),
    ]
    for candidate in candidates:
        if candidate in mappings:
            return mappings[candidate]
    return str(cleaned)


def standardize_team_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Standardize selected team-name columns and write unknown names for review."""
    mappings = load_team_name_map()
    unknown = []
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            continue
        raw_values = result[column].dropna().astype(str).str.strip().unique()
        known_keys = set(mappings) | {_ascii_fold(key).lower() for key in mappings}
        for value in raw_values:
            folded = _ascii_fold(value).lower()
            if value not in mappings and folded not in known_keys:
                unknown.append({"raw_team_name": value, "source_column": column})
        result[column] = result[column].apply(lambda value: standardize_team_name(value, mappings))

    if unknown:
        report = pd.DataFrame(unknown).drop_duplicates()
        UNMAPPED_TEAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(UNMAPPED_TEAMS_PATH, index=False)
        logger.info("Saved %s unmapped team names to %s", len(report), UNMAPPED_TEAMS_PATH)
    return result


def initialize_team_name_map() -> Path:
    """Create the starter team-name map if missing."""
    path = PROCESSED_DIR / "team_name_map.csv"
    if not path.exists():
        rows = [
            {"raw_team_name": raw, "standard_team_name": standard, "source": "built_in_default"}
            for raw, standard in DEFAULT_TEAM_MAPPINGS.items()
        ]
        save_csv(pd.DataFrame(rows), path, TEAM_NAME_MAP_COLUMNS)
    return path
