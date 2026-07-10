"""Kaggle dataset download helpers."""

from pathlib import Path
import os
import zipfile

import pandas as pd

from src.config import KAGGLE_API_TOKEN, KAGGLE_KEY, KAGGLE_USERNAME, RAW_KAGGLE_DIR, REPORTS_DIR
from src.logger import get_logger
from src.utils.files import append_fetch_log

logger = get_logger(__name__)


DATASETS = {
    "international_results": {
        "slug": "martj42/international-football-results-from-1872-to-2017",
        "output_dir": RAW_KAGGLE_DIR / "international_results",
        "url": "https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017",
    },
    "world_cup_historical": {
        "slug": "piterfm/fifa-football-world-cup",
        "output_dir": RAW_KAGGLE_DIR / "world_cup_historical",
        "url": "https://www.kaggle.com/datasets/piterfm/fifa-football-world-cup",
    },
    "world_cup_2026_schedule": {
        "slug": "areezvisram12/fifa-world-cup-2026-match-data-unofficial",
        "output_dir": RAW_KAGGLE_DIR / "world_cup_2026_schedule",
        "url": "https://www.kaggle.com/datasets/areezvisram12/fifa-world-cup-2026-match-data-unofficial",
    },
}


def _has_kaggle_credentials() -> bool:
    return bool(KAGGLE_API_TOKEN or (KAGGLE_USERNAME and KAGGLE_KEY))


def _configure_kaggle_auth() -> str:
    if KAGGLE_API_TOKEN:
        access_token = Path.home() / ".kaggle" / "access_token"
        access_token.parent.mkdir(parents=True, exist_ok=True)
        # Kaggle's API can read this token file; it is outside the project and never logged.
        access_token.write_text(KAGGLE_API_TOKEN, encoding="utf-8")
        try:
            access_token.chmod(0o600)
        except Exception:
            pass
        return "KAGGLE_API_TOKEN"
    os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME or ""
    os.environ["KAGGLE_KEY"] = KAGGLE_KEY or ""
    return "KAGGLE_USERNAME/KAGGLE_KEY"


def _manual_instructions(dataset_slug: str, output_dir: Path) -> str:
    return (
        "Kaggle credentials are missing. Add KAGGLE_USERNAME and KAGGLE_KEY to .env "
        f"or manually download https://www.kaggle.com/datasets/{dataset_slug} "
        f"and place the CSV files in {output_dir}."
    )


def download_kaggle_dataset(dataset_slug: str, output_dir: Path) -> dict:
    """Download and unzip a Kaggle dataset when credentials are configured."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if not _has_kaggle_credentials():
        message = _manual_instructions(dataset_slug, output_dir)
        logger.warning(message)
        append_fetch_log(
            source="kaggle",
            source_url=f"https://www.kaggle.com/datasets/{dataset_slug}",
            status="skipped",
            notes=message,
        )
        return {
            "source": "kaggle",
            "status": "skipped",
            "rows_fetched": 0,
            "output_file": str(output_dir),
            "error_message": message,
        }

    try:
        _configure_kaggle_auth()
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(dataset_slug, path=str(output_dir), unzip=False, quiet=True)
        zip_files = list(output_dir.glob("*.zip"))
        for zip_path in zip_files:
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(output_dir)
            zip_path.unlink()
        row_count = sum(1 for _ in output_dir.glob("*.csv"))
        append_fetch_log(
            source="kaggle",
            source_url=f"https://www.kaggle.com/datasets/{dataset_slug}",
            status="success",
            rows_fetched=row_count,
            raw_output_path=str(output_dir),
        )
        return {
            "source": "kaggle",
            "status": "success",
            "rows_fetched": row_count,
            "output_file": str(output_dir),
            "error_message": "",
        }
    except Exception as exc:
        logger.exception("Kaggle download failed for %s", dataset_slug)
        append_fetch_log(
            source="kaggle",
            source_url=f"https://www.kaggle.com/datasets/{dataset_slug}",
            status="failed",
            raw_output_path=str(output_dir),
            notes=str(exc),
        )
        return {
            "source": "kaggle",
            "status": "failed",
            "rows_fetched": 0,
            "output_file": str(output_dir),
            "error_message": str(exc),
        }


def fetch_international_results() -> dict:
    info = DATASETS["international_results"]
    result = download_kaggle_dataset(info["slug"], info["output_dir"])
    result["source"] = "kaggle_international_results"
    return result


def fetch_world_cup_historical() -> dict:
    info = DATASETS["world_cup_historical"]
    result = download_kaggle_dataset(info["slug"], info["output_dir"])
    result["source"] = "kaggle_world_cup_historical"
    return result


def fetch_world_cup_2026_schedule() -> dict:
    info = DATASETS["world_cup_2026_schedule"]
    result = download_kaggle_dataset(info["slug"], info["output_dir"])
    result["source"] = "kaggle_world_cup_2026_schedule"
    return result


def diagnose_kaggle() -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / "kaggle_diagnostic.md"
    auth_method = "KAGGLE_API_TOKEN" if KAGGLE_API_TOKEN else "KAGGLE_USERNAME/KAGGLE_KEY" if KAGGLE_USERNAME and KAGGLE_KEY else "none"
    rows = []
    if auth_method == "none":
        for info in DATASETS.values():
            rows.append([info["slug"], "no", "skipped", "missing Kaggle credentials", "Add KAGGLE_API_TOKEN or KAGGLE_USERNAME/KAGGLE_KEY to .env"])
    else:
        try:
            _configure_kaggle_auth()
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
            for info in DATASETS.values():
                try:
                    api.dataset_metadata(info["slug"], path=str(info["output_dir"]))
                    rows.append([info["slug"], "yes", "reachable", "", "Run load-real-data to download and clean"])
                except Exception as exc:
                    rows.append([info["slug"], "no", "failed", str(exc), "Check Kaggle account access or download manually"])
        except Exception as exc:
            for info in DATASETS.values():
                rows.append([info["slug"], "no", "auth failed", str(exc), "Check Kaggle credentials in .env"])
    lines = [
        "# Kaggle Diagnostic",
        "",
        f"- Authentication method detected: {auth_method}",
        "- Secret values: hidden",
        "",
        "| Dataset | Reachable | Status | Issue | Next Action |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "success" if any(row[1] == "yes" for row in rows) else "failed", "report": str(md_path)}


def write_kaggle_file_inventory() -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, info in DATASETS.items():
        folder = info["output_dir"]
        for path in sorted(folder.rglob("*.csv")):
            try:
                df = pd.read_csv(path, nrows=1000)
                full_rows = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
                columns = list(df.columns)
                lower = {column.lower() for column in columns}
                if {"home_team", "away_team"}.issubset(lower) or {"home score", "away score"}.issubset(lower):
                    purpose = "match results"
                elif "fixture" in " ".join(lower) or "date" in lower:
                    purpose = "possible fixtures"
                else:
                    purpose = "unknown"
                used = "yes" if purpose in {"match results", "possible fixtures"} else "no"
                reason = "columns match expected match/fixture shape" if used == "yes" else "columns did not match expected cleaners"
            except Exception as exc:
                full_rows, columns, purpose, used, reason = 0, [], "invalid", "no", str(exc)
            rows.append([name, str(folder), path.name, full_rows, ", ".join(columns), purpose, used, reason])
    lines = [
        "# Kaggle File Inventory",
        "",
        "| dataset | raw folder | file name | row count | columns | likely purpose | used yes/no | reason |",
        "|---|---|---|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    if not rows:
        lines.append("| none | none | none | 0 | none | none | no | No Kaggle CSV files found yet. |")
    path = REPORTS_DIR / "kaggle_file_inventory.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
