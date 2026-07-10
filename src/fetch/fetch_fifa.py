"""Official FIFA Data Centre fetcher."""

from io import StringIO

import pandas as pd

from src.cleaning.clean_matches import clean_2026_fixtures, clean_2026_results
from src.config import PROCESSED_DIR, RAW_FIFA_DIR
from src.logger import get_logger
from src.utils.files import append_fetch_log
from src.utils.http import get_text

logger = get_logger(__name__)

FIFA_MATCHES_URL = "https://inside.fifa.com/data-centre/matches"


def fetch_fifa_data_centre_matches() -> dict:
    raw_output = RAW_FIFA_DIR / "fifa_matches_raw.csv"
    note_output = RAW_FIFA_DIR / "fifa_data_centre_manual_fallback.txt"
    try:
        html = get_text(FIFA_MATCHES_URL, timeout=30)
        tables = pd.read_html(StringIO(html))
        if not tables:
            raise ValueError("FIFA page loaded but no parseable HTML tables were found.")
        table = max(tables, key=len)
        table.to_csv(raw_output, index=False)
        raw_2026 = RAW_FIFA_DIR / "fifa_2026_matches_raw.csv"
        table.to_csv(raw_2026, index=False)
        append_fetch_log("fifa_data_centre", FIFA_MATCHES_URL, "success", len(table), str(raw_output))
        return {"source": "fifa_data_centre", "status": "success", "rows_fetched": len(table), "output_file": str(raw_output), "error_message": ""}
    except Exception as exc:
        message = (
            "FIFA Data Centre could not be parsed as static HTML. It may be JavaScript-rendered. "
            "Use a manual CSV export, API-Football, or another official API if available."
        )
        note_output.write_text(f"{message}\n\nOriginal error: {exc}\n", encoding="utf-8")
        logger.warning("%s Error: %s", message, exc)
        append_fetch_log("fifa_data_centre", FIFA_MATCHES_URL, "skipped", raw_output_path=str(note_output), notes=f"{message} {exc}")
        return {"source": "fifa_data_centre", "status": "skipped", "rows_fetched": 0, "output_file": str(note_output), "error_message": str(exc)}


def clean_fifa_matches() -> dict:
    """Best-effort conversion of fetched FIFA data into processed fixtures/results."""
    raw_path = RAW_FIFA_DIR / "fifa_2026_matches_raw.csv"
    if not raw_path.exists():
        return {"source": "fifa_clean", "status": "skipped", "rows_fetched": 0, "output_file": "", "error_message": "No FIFA raw CSV found."}
    try:
        df = pd.read_csv(raw_path)
        output = PROCESSED_DIR / "fixtures_2026_fifa.csv"
        df.to_csv(output, index=False)
        clean_2026_fixtures()
        clean_2026_results()
        return {"source": "fifa_clean", "status": "success", "rows_fetched": len(df), "output_file": str(output), "error_message": ""}
    except Exception as exc:
        logger.exception("FIFA clean failed")
        return {"source": "fifa_clean", "status": "failed", "rows_fetched": 0, "output_file": "", "error_message": str(exc)}

