"""Project configuration and filesystem paths."""

from pathlib import Path
from typing import Optional

import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
BACKUPS_DIR = DATA_DIR / "backups"

RAW_KAGGLE_DIR = RAW_DIR / "kaggle"
RAW_FIFA_DIR = RAW_DIR / "fifa"
RAW_FBREF_DIR = RAW_DIR / "fbref"
RAW_ELO_DIR = RAW_DIR / "elo"
RAW_API_FOOTBALL_DIR = RAW_DIR / "api_football"
RAW_MANUAL_DIR = RAW_DIR / "manual"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"

FETCH_LOG_PATH = METADATA_DIR / "fetch_log.csv"
DATA_SOURCES_PATH = METADATA_DIR / "data_sources.csv"
PIPELINE_LOG_PATH = REPORTS_DIR / "fetch_pipeline.log"
UPDATE_LOG_PATH = REPORTS_DIR / "update_pipeline.log"
VALIDATION_REPORT_PATH = REPORTS_DIR / "data_validation_report.csv"
UNMAPPED_TEAMS_PATH = REPORTS_DIR / "unmapped_team_names.csv"
UPDATE_STATE_PATH = METADATA_DIR / "update_state.json"
LATEST_REFRESH_SUMMARY_MD = REPORTS_DIR / "latest_refresh_summary.md"
LATEST_REFRESH_SUMMARY_JSON = REPORTS_DIR / "latest_refresh_summary.json"

load_dotenv(PROJECT_ROOT / ".env")

API_FOOTBALL_KEY: Optional[str] = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_WORLD_CUP_LEAGUE_ID: Optional[str] = os.getenv("API_FOOTBALL_WORLD_CUP_LEAGUE_ID")
SPORTMONKS_KEY: Optional[str] = os.getenv("SPORTMONKS_KEY")
KAGGLE_API_TOKEN: Optional[str] = os.getenv("KAGGLE_API_TOKEN")
KAGGLE_USERNAME: Optional[str] = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY: Optional[str] = os.getenv("KAGGLE_KEY")
FOOTBALL_DATA_ORG_KEY: Optional[str] = os.getenv("FOOTBALL_DATA_ORG_KEY")
FOOTBALL_DATA_ORG_COMPETITION_ID: str = os.getenv("FOOTBALL_DATA_ORG_COMPETITION_ID", "2000")
FOOTBALL_DATA_ORG_COMPETITION_CODE: str = os.getenv("FOOTBALL_DATA_ORG_COMPETITION_CODE", "WC")
FOOTBALL_DATA_ORG_SEASON: str = os.getenv("FOOTBALL_DATA_ORG_SEASON", "2026")


def ensure_project_directories() -> None:
    """Create the folders used by the data pipeline."""
    directories = [
        RAW_KAGGLE_DIR / "international_results",
        RAW_KAGGLE_DIR / "world_cup_historical",
        RAW_KAGGLE_DIR / "world_cup_2026_schedule",
        RAW_FIFA_DIR,
        RAW_FBREF_DIR,
        RAW_ELO_DIR,
        RAW_API_FOOTBALL_DIR,
        RAW_MANUAL_DIR,
        PROCESSED_DIR,
        METADATA_DIR,
        BACKUPS_DIR,
        REPORTS_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
