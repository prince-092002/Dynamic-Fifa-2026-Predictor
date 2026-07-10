"""Source priority and quality-gate configuration for live forecasts."""

from __future__ import annotations

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR

SOURCE_SNAPSHOT_DIR = LIVE_STATE_DIR / "source_snapshots"
SOURCE_VERIFICATION_REPORT_DIR = LIVE_REPORT_DIR / "source_verification"

SOURCE_PRIORITY = [
    {
        "source": "api_football_live_api",
        "priority": 1,
        "purpose": "fixtures, statuses, completed results, rounds, standings, teams, and knockout fixtures",
    },
    {
        "source": "football_data_org",
        "priority": 2,
        "purpose": "alternative World Cup provider when API-Football blocks 2026 by plan or season availability",
    },
    {
        "source": "fifa_official",
        "priority": 3,
        "purpose": "official verification when parseable without aggressive scraping",
    },
    {
        "source": "secondary_public_sources",
        "priority": 4,
        "purpose": "sanity-check only; do not replace primary data by default",
    },
    {
        "source": "local_processed_csv",
        "priority": 5,
        "purpose": "fallback when live sources fail",
    },
    {
        "source": "fallback_bracket_template",
        "priority": 6,
        "purpose": "last-resort structure only; never official and never true-live",
    },
]

FORECAST_MODES = [
    "true_live_forecast",
    "partially_live_forecast",
    "fallback_pre_tournament_forecast",
    "insufficient_data",
]

SOURCE_QUALITY_LEVELS = {
    "high": "live fixtures/results plus standings/bracket from API or FIFA",
    "medium": "live fixtures/results available, standings computed locally, bracket partly fallback",
    "low": "no completed live results and fallback bracket mostly used",
    "invalid": "no reliable live fixtures/current state",
}

PUBLIC_LABELS = {
    "true_live_forecast": "True live forecast from current tournament state",
    "partially_live_forecast": "Partially live forecast with fallback assumptions",
    "fallback_pre_tournament_forecast": "Pre-tournament fallback forecast, not based on completed 2026 results",
    "insufficient_data": "Insufficient live data for finalist forecast",
}


def ensure_source_verification_directories() -> None:
    SOURCE_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_VERIFICATION_REPORT_DIR.mkdir(parents=True, exist_ok=True)
