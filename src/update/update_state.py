"""Persistent state for automatic data refreshes."""

import json
import shutil
from pathlib import Path
from typing import Any

from src.config import UPDATE_STATE_PATH, ensure_project_directories
from src.utils.dates import now_utc_iso


DEFAULT_UPDATE_STATE = {
    "last_refresh_time": "",
    "last_update_mode": "",
    "last_update_status": "",
    "last_successful_source": "",
    "last_completed_match_ids": [],
    "latest_result_count": 0,
    "latest_fixture_count": 0,
    "last_error": "",
}


def _default_state() -> dict[str, Any]:
    return dict(DEFAULT_UPDATE_STATE)


def load_update_state() -> dict[str, Any]:
    """Load update_state.json, recreating it safely when missing or corrupted."""
    ensure_project_directories()
    if not UPDATE_STATE_PATH.exists():
        state = _default_state()
        save_update_state(state)
        return state

    try:
        state = json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
        merged = _default_state()
        merged.update(state)
        if not isinstance(merged.get("last_completed_match_ids"), list):
            merged["last_completed_match_ids"] = []
        return merged
    except (json.JSONDecodeError, OSError):
        backup_path = UPDATE_STATE_PATH.with_name(
            f"update_state_corrupted_{now_utc_iso().replace(':', '').replace('-', '')}.json"
        )
        shutil.copy2(UPDATE_STATE_PATH, backup_path)
        state = _default_state()
        state["last_error"] = f"Corrupted update state backed up to {backup_path}"
        save_update_state(state)
        return state


def save_update_state(state: dict[str, Any]) -> Path:
    """Save update state atomically through a temporary JSON file."""
    ensure_project_directories()
    merged = _default_state()
    merged.update(state)
    temp_path = UPDATE_STATE_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    temp_path.replace(UPDATE_STATE_PATH)
    return UPDATE_STATE_PATH


def get_last_completed_match_ids() -> list[str]:
    state = load_update_state()
    return [str(match_id) for match_id in state.get("last_completed_match_ids", [])]


def update_completed_match_ids(match_ids: list[str]) -> Path:
    state = load_update_state()
    state["last_completed_match_ids"] = sorted({str(match_id) for match_id in match_ids if str(match_id).strip()})
    state["last_refresh_time"] = now_utc_iso()
    return save_update_state(state)


def reset_update_state() -> Path:
    return save_update_state(_default_state())

