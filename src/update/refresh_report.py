"""Refresh summary report writer."""

import json
from typing import Any

from src.config import LATEST_REFRESH_SUMMARY_JSON, LATEST_REFRESH_SUMMARY_MD


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def write_refresh_summary(result: dict[str, Any]) -> tuple[str, str]:
    """Write latest refresh summary in Markdown and JSON."""
    LATEST_REFRESH_SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    LATEST_REFRESH_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)

    warnings = result.get("warnings", []) or []
    errors = result.get("errors", []) or []
    files_updated = result.get("files_updated", []) or []

    markdown = [
        "# Latest Refresh Summary",
        "",
        f"- Refresh timestamp: {result.get('refresh_timestamp', '')}",
        f"- Mode used: {result.get('mode', '')}",
        f"- Force refresh: {_yes_no(bool(result.get('force', False)))}",
        f"- Source used: {result.get('source_used', '')}",
        f"- API key available: {_yes_no(bool(result.get('api_key_available', False)))}",
        f"- Fixtures fetched: {result.get('fixtures_fetched', 0)}",
        f"- Completed results count: {result.get('completed_results_count', 0)}",
        f"- New completed matches detected: {result.get('new_completed_matches_detected', 0)}",
        f"- Files updated: {', '.join(files_updated) if files_updated else 'none'}",
        f"- Backup folder created: {result.get('backup_folder') or 'none'}",
        f"- Validation status: {result.get('validation_status', 'unknown')}",
        f"- Errors or warnings: {'; '.join(errors + warnings) if errors or warnings else 'none'}",
        f"- Next recommended action: {result.get('next_recommended_action', '')}",
        "",
    ]
    LATEST_REFRESH_SUMMARY_MD.write_text("\n".join(markdown), encoding="utf-8")
    LATEST_REFRESH_SUMMARY_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return str(LATEST_REFRESH_SUMMARY_MD), str(LATEST_REFRESH_SUMMARY_JSON)

