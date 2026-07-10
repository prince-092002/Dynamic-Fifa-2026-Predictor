"""Shared row-count, manual-data, security, and readiness reports."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR, PROJECT_ROOT, RAW_MANUAL_DIR, REPORTS_DIR, ensure_project_directories
from src.loading.manual_sources import MANUAL_FILES
from src.loading.reports import PROCESSED_REQUIREMENTS
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    PLAYER_STATS_COLUMNS,
    RESULTS_2026_COLUMNS,
    TEAM_RATINGS_COLUMNS,
    TEAM_STATS_COLUMNS,
)

DATA_SUMMARY_FILES = [
    "historical_international_matches.csv",
    "historical_world_cup_matches.csv",
    "matches_master.csv",
    "fixtures_2026.csv",
    "results_2026.csv",
    "team_ratings.csv",
    "team_stats_2026.csv",
    "player_stats_2026.csv",
    "team_name_map.csv",
]


def csv_status(path: Path, required_columns: list[str] | None = None) -> dict:
    if not path.exists():
        return {"exists": False, "rows": 0, "columns": "", "status": "MISSING", "last_modified": ""}
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return {
            "exists": True,
            "rows": 0,
            "columns": "",
            "status": "INVALID",
            "last_modified": _mtime(path),
            "issue": str(exc),
        }
    columns = list(df.columns)
    missing = [column for column in (required_columns or []) if column not in columns]
    if missing:
        status = "INVALID"
    elif df.empty:
        status = "HEADER-ONLY"
    else:
        critical = [column for column in (required_columns or columns) if column not in {"source", "last_updated", "is_draw", "neutral"}]
        useful = df[[column for column in critical if column in df.columns]].notna().any(axis=1).any() if critical else not df.empty
        status = "REAL DATA" if useful else "HEADER-ONLY"
    return {
        "exists": True,
        "rows": int(len(df)),
        "columns": ", ".join(columns),
        "status": status,
        "last_modified": _mtime(path),
        "missing_columns": ", ".join(missing),
    }


def _mtime(path: Path) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def write_data_summary(print_table: bool = False) -> dict:
    ensure_project_directories()
    rows = []
    for filename in DATA_SUMMARY_FILES:
        path = PROCESSED_DIR / filename
        required = PROCESSED_REQUIREMENTS.get(filename, [])
        info = csv_status(path, required)
        rows.append(
            {
                "Processed file": f"data/processed/{filename}",
                "Exists": "yes" if info["exists"] else "no",
                "Rows": info["rows"],
                "Columns": info["columns"],
                "Real-data status": info["status"],
                "Last modified": info["last_modified"],
            }
        )
    df = pd.DataFrame(rows)
    csv_path = REPORTS_DIR / "data_summary.csv"
    md_path = REPORTS_DIR / "data_summary.md"
    df.to_csv(csv_path, index=False)
    lines = [
        "# Data Summary",
        "",
        "| Processed file | Exists | Rows | Real-data status | Last modified |",
        "|---|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['Processed file']}` | {row['Exists']} | {row['Rows']} | {row['Real-data status']} | {row['Last modified']} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    if print_table:
        print(df[["Processed file", "Exists", "Rows", "Real-data status", "Last modified"]].to_string(index=False))
    return {"rows": rows, "csv": str(csv_path), "md": str(md_path)}


def write_feature_readiness_gate(print_result: bool = False) -> dict:
    required = ["matches_master.csv", "fixtures_2026.csv", "team_ratings.csv"]
    recommended = ["results_2026.csv", "team_stats_2026.csv"]
    checks = []
    for filename in required + recommended:
        info = csv_status(PROCESSED_DIR / filename, PROCESSED_REQUIREMENTS.get(filename, []))
        checks.append((filename, info))
    ready = all(info["status"] == "REAL DATA" for filename, info in checks if filename in required)
    missing = [filename for filename, info in checks if filename in required and info["status"] != "REAL DATA"]
    lines = [
        "# Feature Readiness Gate",
        "",
        f"READY_FOR_FEATURE_ENGINEERING = {'TRUE' if ready else 'FALSE'}",
        "",
        "| File | Required | Rows | Status |",
        "|---|---|---:|---|",
    ]
    for filename, info in checks:
        lines.append(f"| `data/processed/{filename}` | {'yes' if filename in required else 'recommended'} | {info['rows']} | {info['status']} |")
    lines.extend(["", "## Exact Next Action", ""])
    if ready:
        lines.append("Core files have real rows. You can start feature engineering; recommended files can still improve model strength.")
    else:
        lines.append("Load or provide real rows for: " + ", ".join(f"`data/processed/{name}`" for name in missing) + ".")
        lines.append("Run `python main.py load-real-data --debug` after adding credentials or manual fallback CSV rows.")
    path = REPORTS_DIR / "feature_readiness_gate.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    if print_result:
        print(f"READY_FOR_FEATURE_ENGINEERING = {'TRUE' if ready else 'FALSE'}")
    return {"ready": ready, "report": str(path), "missing": missing}


def write_manual_data_validation(print_table: bool = False) -> str:
    requirements = {
        "manual_fixtures_2026.csv": FIXTURES_2026_COLUMNS,
        "manual_results_2026.csv": RESULTS_2026_COLUMNS,
        "manual_team_ratings.csv": TEAM_RATINGS_COLUMNS,
        "manual_team_stats_2026.csv": TEAM_STATS_COLUMNS,
        "manual_player_stats_2026.csv": PLAYER_STATS_COLUMNS,
    }
    rows = []
    for filename, required in requirements.items():
        info = csv_status(RAW_MANUAL_DIR / filename, required)
        status = info["status"]
        if status in {"MISSING", "HEADER-ONLY"} and (RAW_MANUAL_DIR / filename.replace(".csv", "_template.csv")).exists():
            status = "HEADER-ONLY TEMPLATE"
        rows.append({"Manual file": f"data/raw/manual/{filename}", "Rows": info["rows"], "Status": status, "Missing columns": info.get("missing_columns", "")})
    lines = ["# Manual Data Validation", "", "| Manual file | Rows | Status | Missing columns |", "|---|---:|---|---|"]
    for row in rows:
        lines.append(f"| `{row['Manual file']}` | {row['Rows']} | {row['Status']} | {row['Missing columns']} |")
    path = REPORTS_DIR / "manual_data_validation.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    if print_table:
        print(pd.DataFrame(rows).to_string(index=False))
    return str(path)


def write_security_check_report() -> str:
    required_ignores = [
        ".env",
        "*.env",
        "kaggle.json",
        "access_token",
        ".kaggle/",
        "**pycache**/",
        "*.pyc",
        "data/raw/api_football/*.json",
        "outputs/reports/*diagnostic*.json",
    ]
    gitignore = PROJECT_ROOT / ".gitignore"
    env_example = PROJECT_ROOT / ".env.example"
    ignore_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    env_text = env_example.read_text(encoding="utf-8") if env_example.exists() else ""
    env_safe = all(line.endswith("=") for line in env_text.splitlines() if line.strip() and not line.startswith("#"))
    secret_patterns = [r"KGAT_[A-Za-z0-9_-]+", r"[A-Fa-f0-9]{40,}", r"x-apisports-key\s*[:=]\s*['\"][^'\"]+"]
    findings = []
    checked = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir() or ".env" == path.name or path.parts[-2:] == ("api_football", path.name):
            continue
        if path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".csv", ".example", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        checked.append(str(path.relative_to(PROJECT_ROOT)))
        for pattern in secret_patterns:
            if re.search(pattern, text):
                findings.append(str(path.relative_to(PROJECT_ROOT)))
                break
    lines = [
        "# Security Check Report",
        "",
        f"- `.gitignore` protects required secret patterns: {'yes' if all(item in ignore_text for item in required_ignores) else 'no'}",
        f"- `.env.example` contains placeholders only: {'yes' if env_safe else 'no'}",
        f"- Hardcoded secret-like values found: {'yes' if findings else 'no'}",
        "",
        "## Files Checked",
        "",
    ]
    lines.extend(f"- `{item}`" for item in checked[:200])
    if findings:
        lines.extend(["", "## Recommended User Action", "", "Rotate any exposed secret, remove it from files, and keep credentials only in `.env`."])
        lines.extend(f"- Possible secret-like content in `{item}`" for item in sorted(set(findings)))
    else:
        lines.extend(["", "## Recommended User Action", "", "Keep `.env` local and never paste credential values into code, reports, logs, or README."])
    path = REPORTS_DIR / "security_check_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
