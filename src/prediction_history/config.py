"""Paths and constants for the prediction-history snapshot store."""

from __future__ import annotations

from src.config import PROJECT_ROOT

SCHEMA_VERSION = "1.0"

PUBLIC_DATA_DIR = PROJECT_ROOT / "public_data"
HISTORY_DIR = PROJECT_ROOT / "data" / "prediction_history"
SNAPSHOTS_DIR = HISTORY_DIR / "snapshots"
MANIFEST_PATH = HISTORY_DIR / "manifest.json"

# Provenance classes (honesty labels shown in the UI).
RECORD_GENUINE = "genuine_archived_forecast"          # archived live during a production refresh
RECORD_RECOVERED = "recovered_from_committed_output"  # rebuilt from a real committed public_data forecast


def ensure_dirs() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
