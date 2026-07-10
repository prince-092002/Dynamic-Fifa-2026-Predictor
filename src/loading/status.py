"""Small helpers for source-status rows."""

from typing import Any


SOURCE_STATUS_COLUMNS = [
    "Source",
    "Purpose",
    "Credential required",
    "Status",
    "Rows fetched",
    "Raw output path",
    "Processed output path",
    "Issue",
    "Next action",
]


def source_row(
    source: str,
    purpose: str,
    credential_required: str,
    status: str,
    rows_fetched: int = 0,
    raw_output_path: str = "",
    processed_output_path: str = "",
    issue: str = "",
    next_action: str = "",
) -> dict[str, Any]:
    return {
        "Source": source,
        "Purpose": purpose,
        "Credential required": credential_required,
        "Status": status,
        "Rows fetched": int(rows_fetched or 0),
        "Raw output path": raw_output_path,
        "Processed output path": processed_output_path,
        "Issue": issue,
        "Next action": next_action,
    }

