"""Paths and constants for the Zafronix enrichment pipeline."""

from __future__ import annotations

from src.config import DATA_DIR, OUTPUTS_DIR

# Raw sanitized snapshots (gitignored, bulky).
RAW_DIR = DATA_DIR / "raw" / "zafronix"
SNAPSHOT_DIR = RAW_DIR / "snapshots"

# Normalized, small, tracked tables.
PROCESSED_DIR = DATA_DIR / "processed" / "zafronix"
TOURNAMENTS_CSV = PROCESSED_DIR / "zafronix_tournaments.csv"
APPEARANCES_CSV = PROCESSED_DIR / "zafronix_team_appearances.csv"
SQUADS_CSV = PROCESSED_DIR / "zafronix_squad_players.csv"

# Enrichment features + reports.
FEATURES_DIR = DATA_DIR / "features" / "zafronix"
REPORT_DIR = OUTPUTS_DIR / "reports" / "enrichment" / "zafronix"

# Challenger model artifacts (joblib binaries gitignored; metrics/JSON tracked).
MODEL_DIR = OUTPUTS_DIR / "models" / "phase5h_zafronix"


def ensure_dirs() -> None:
    for path in [RAW_DIR, SNAPSHOT_DIR, PROCESSED_DIR, FEATURES_DIR, REPORT_DIR, MODEL_DIR]:
        path.mkdir(parents=True, exist_ok=True)
