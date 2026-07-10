"""Reports for source status, manual data needs, API status, and data readiness."""

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import PROCESSED_DIR, PROJECT_ROOT, REPORTS_DIR, UPDATE_STATE_PATH
from src.loading.status import SOURCE_STATUS_COLUMNS
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    MATCHES_MASTER_COLUMNS,
    PLAYER_STATS_COLUMNS,
    RESULTS_2026_COLUMNS,
    TEAM_RATINGS_COLUMNS,
    TEAM_STATS_COLUMNS,
    has_real_rows,
    read_csv_if_exists,
)


SOURCE_STATUS_REPORT_PATH = REPORTS_DIR / "source_status_report.md"
MANUAL_DATA_NEEDED_PATH = REPORTS_DIR / "manual_data_needed.md"
API_FOOTBALL_STATUS_PATH = REPORTS_DIR / "api_football_status.md"
DATA_READINESS_REPORT_PATH = REPORTS_DIR / "data_readiness_report.md"


PROCESSED_REQUIREMENTS = {
    "matches_master.csv": MATCHES_MASTER_COLUMNS,
    "historical_international_matches.csv": [
        "date",
        "team_a",
        "team_b",
        "team_a_goals",
        "team_b_goals",
        "tournament",
        "city",
        "country",
        "neutral",
        "winner",
        "is_draw",
        "source",
        "last_updated",
    ],
    "historical_world_cup_matches.csv": [
        "date",
        "team_a",
        "team_b",
        "team_a_goals",
        "team_b_goals",
        "tournament",
        "city",
        "country",
        "neutral",
        "winner",
        "is_draw",
        "source",
        "last_updated",
    ],
    "fixtures_2026.csv": FIXTURES_2026_COLUMNS,
    "results_2026.csv": RESULTS_2026_COLUMNS,
    "team_ratings.csv": TEAM_RATINGS_COLUMNS,
    "team_stats_2026.csv": TEAM_STATS_COLUMNS,
    "player_stats_2026.csv": PLAYER_STATS_COLUMNS,
    "team_name_map.csv": ["raw_team_name", "standard_team_name", "source"],
}


def _row_count(path: Path) -> int:
    try:
        return len(pd.read_csv(path)) if path.exists() and path.stat().st_size > 0 else 0
    except Exception:
        return 0


def write_source_status_report(rows: list[dict]) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for column in SOURCE_STATUS_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    df = df[SOURCE_STATUS_COLUMNS]

    lines = [
        "# Source Status Report",
        "",
        "| Source | Purpose | Credential required | Status | Rows fetched | Raw output path | Processed output path | Issue | Next action |",
        "|---|---|---|---|---:|---|---|---|---|",
    ]
    for _, row in df.iterrows():
        values = [str(row[column]).replace("|", "\\|") for column in SOURCE_STATUS_COLUMNS]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    SOURCE_STATUS_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(SOURCE_STATUS_REPORT_PATH)


def write_manual_data_needed_report(items: Iterable[str]) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    unique_items = [item for item in dict.fromkeys(items) if item]
    lines = ["# Manual Data Needed", ""]
    if unique_items:
        lines.append("The following data is still missing or empty:")
        lines.append("")
        for item in unique_items:
            lines.append(f"- {item}")
    else:
        lines.append("No manual data gaps were detected.")
    lines.extend(
        [
            "",
            "Use the non-template filenames when adding real data:",
            "",
            "- `data/raw/manual/manual_fixtures_2026.csv`",
            "- `data/raw/manual/manual_results_2026.csv`",
            "- `data/raw/manual/manual_team_ratings.csv`",
            "- `data/raw/manual/manual_team_stats_2026.csv`",
            "- `data/raw/manual/manual_player_stats_2026.csv`",
            "",
            "Template files are useful for column reference, but header-only templates are not real data.",
        ]
    )
    MANUAL_DATA_NEEDED_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(MANUAL_DATA_NEEDED_PATH)


def write_api_football_status(status: str, message: str, raw_output_path: str = "") -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# API-Football Status",
        "",
        f"- Status: {status}",
        f"- Message: {message}",
        f"- Raw output path: {raw_output_path or 'none'}",
        "",
        "No API secrets are printed in this report.",
    ]
    API_FOOTBALL_STATUS_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(API_FOOTBALL_STATUS_PATH)


def generate_data_readiness_report(source_rows: list[dict] | None = None) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    inventory = []
    for filename, required in PROCESSED_REQUIREMENTS.items():
        path = PROCESSED_DIR / filename
        rows = _row_count(path)
        real = has_real_rows(path, required)
        inventory.append((filename, rows, real))

    required_ready = all(
        has_real_rows(PROCESSED_DIR / filename, PROCESSED_REQUIREMENTS[filename])
        for filename in ["matches_master.csv", "fixtures_2026.csv", "team_ratings.csv"]
    )
    stronger_ready = required_ready and all(
        has_real_rows(PROCESSED_DIR / filename, PROCESSED_REQUIREMENTS[filename])
        for filename in ["results_2026.csv", "team_stats_2026.csv"]
    )

    update_state_valid = False
    if UPDATE_STATE_PATH.exists():
        try:
            import json

            json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
            update_state_valid = True
        except Exception:
            update_state_valid = False

    worked = []
    failed = []
    for row in source_rows or []:
        if str(row.get("Status", "")).lower() in {"success", "loaded", "available"} and int(row.get("Rows fetched", 0) or 0) > 0:
            worked.append(row.get("Source", "unknown"))
        elif str(row.get("Status", "")).lower() not in {"success", "loaded", "available"}:
            failed.append(row.get("Source", "unknown"))

    missing_core = [
        filename
        for filename in ["matches_master.csv", "fixtures_2026.csv", "team_ratings.csv"]
        if not has_real_rows(PROCESSED_DIR / filename, PROCESSED_REQUIREMENTS[filename])
    ]
    missing_stronger = [
        filename
        for filename in ["results_2026.csv", "team_stats_2026.csv"]
        if not has_real_rows(PROCESSED_DIR / filename, PROCESSED_REQUIREMENTS[filename])
    ]

    lines = [
        "# Data Readiness Report",
        "",
        f"Project root: `{PROJECT_ROOT}`",
        "",
        "## Processed File Row Counts",
        "",
        "| File | Rows | Real-data ready |",
        "|---|---:|---|",
    ]
    for filename, rows, real in inventory:
        lines.append(f"| `data/processed/{filename}` | {rows} | {'yes' if real else 'no'} |")

    lines.extend(
        [
            "",
            "## Update State",
            "",
            f"- `data/metadata/update_state.json` exists: {'yes' if UPDATE_STATE_PATH.exists() else 'no'}",
            f"- `data/metadata/update_state.json` is valid JSON: {'yes' if update_state_valid else 'no'}",
            "",
            "## Source Outcomes",
            "",
            f"- Sources with real rows loaded: {', '.join(worked) if worked else 'none'}",
            f"- Sources needing attention: {', '.join(failed) if failed else 'none'}",
            "",
            "## Feature Engineering Readiness",
            "",
            f"- Core readiness: {'TRUE' if required_ready else 'FALSE'}",
            f"- Stronger readiness with results and team stats: {'TRUE' if stronger_ready else 'FALSE'}",
            "",
        ]
    )
    if missing_core:
        lines.append("Core missing files/data before feature engineering:")
        for filename in missing_core:
            lines.append(f"- `data/processed/{filename}`")
        lines.append("")
    if missing_stronger:
        lines.append("Additional missing files/data before stronger modeling:")
        for filename in missing_stronger:
            lines.append(f"- `data/processed/{filename}`")
        lines.append("")

    lines.extend(
        [
            "## Recommendation",
            "",
            "Do not build the model yet unless the core readiness flag is TRUE. Load API/Kaggle credentials or real manual CSV rows, then rerun `python main.py load-real-data`.",
        ]
    )
    DATA_READINESS_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(DATA_READINESS_REPORT_PATH)

