"""Date helpers used across fetchers and cleaners."""

from datetime import datetime, timezone

import pandas as pd


def now_utc_iso() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_date_series(series: pd.Series) -> pd.Series:
    """Parse a pandas Series into ISO date strings where possible."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.strftime("%Y-%m-%d")
