"""Secondary public-source verification reports for live state."""

from __future__ import annotations

import pandas as pd
import requests

from src.live_state.live_source_config import SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories

SECONDARY_SOURCES = [
    {"source": "FIFA official", "url": "https://inside.fifa.com/data-centre/matches"},
    {"source": "ESPN soccer", "url": "https://www.espn.com/soccer/"},
    {"source": "FOX Sports soccer", "url": "https://www.foxsports.com/soccer"},
    {"source": "Reuters sports", "url": "https://www.reuters.com/sports/"},
]


def verify_against_secondary_sources(timeout: int = 12) -> dict:
    ensure_source_verification_directories()
    rows = []
    for item in SECONDARY_SOURCES:
        reachable = False
        parseable = False
        detected = ""
        recommendation = "Unavailable for automated verification; keep API/local state unchanged."
        try:
            response = requests.get(item["url"], timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            reachable = 200 <= response.status_code < 400
            text = response.text[:5000] if reachable else ""
            lowered = text.lower()
            parseable = bool(reachable and ("world cup" in lowered or "fifa" in lowered or "soccer" in lowered))
            detected = "basic page text parseable" if parseable else f"HTTP {response.status_code}"
            if parseable:
                recommendation = "Use only as a sanity-check report; do not overwrite API-Football state by default."
        except Exception as exc:
            detected = str(exc)
        rows.append(
            {
                "source": item["source"],
                "url": item["url"],
                "reachable": reachable,
                "parseable": parseable,
                "detected": detected[:300],
                "matches_api_state": "not_checked",
                "differences": "",
                "recommendation": recommendation,
            }
        )
    df = pd.DataFrame(rows)
    csv_path = SOURCE_VERIFICATION_REPORT_DIR / "secondary_source_verification_report.csv"
    md_path = SOURCE_VERIFICATION_REPORT_DIR / "secondary_source_verification_report.md"
    df.to_csv(csv_path, index=False)
    lines = [
        "# Secondary Source Verification Report",
        "",
        "Secondary sources are sanity checks only. This project does not bypass blocks and does not replace API-Football data with scraped secondary data by default.",
        "",
        "| Source | Reachable | Parseable | Detected | Recommendation |",
        "|---|---|---|---|---|",
    ]
    for _, row in df.iterrows():
        lines.append(f"| {row['source']} | {row['reachable']} | {row['parseable']} | {row['detected']} | {row['recommendation']} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "success", "report": str(md_path), "csv": str(csv_path), "rows": len(df)}

