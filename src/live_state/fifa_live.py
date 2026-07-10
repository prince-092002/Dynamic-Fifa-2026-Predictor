"""Polite FIFA official source checks for live-state availability."""

from __future__ import annotations

from src.live_state.live_config import LIVE_REPORT_DIR, ensure_live_directories
from src.utils.dates import now_utc_iso


def fetch_fifa_official_match_state() -> dict:
    ensure_live_directories()
    path = LIVE_REPORT_DIR / "fifa_official_live_status.md"
    path.write_text(
        "\n".join(
            [
                "# FIFA Official Live Status",
                "",
                f"- Checked at: {now_utc_iso()}",
                "- Status: skipped",
                "- Reason: FIFA match pages are often JavaScript-rendered. This project does not bypass blocks or run aggressive scraping.",
                "- Operational source: API-Football when available; processed CSV fallback otherwise.",
            ]
        ),
        encoding="utf-8",
    )
    return {"status": "skipped", "report": str(path)}


def fetch_fifa_official_bracket_state() -> dict:
    return fetch_fifa_official_match_state()

