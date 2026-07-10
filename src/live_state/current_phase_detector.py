"""Detailed current tournament phase detection."""

from __future__ import annotations

import pandas as pd

from src.live_state.live_config import fixture_status_series, normalize_stage_name
from src.live_state.live_source_config import SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories

COMPLETED_STATUSES = {"completed", "ft", "aet", "pen", "match finished", "finished"}
LIVE_STATUSES = {"live", "1h", "2h", "ht", "et", "p", "in progress"}
SCHEDULED_STATUSES = {"scheduled", "timed", "ns", "tbd", "not started"}

STAGE_ORDER = {
    "Group Stage": 0,
    "Round of 32": 1,
    "Round of 16": 2,
    "Quarterfinal": 3,
    "Semifinal": 4,
    "Final": 5,
}


def _status_series(data: pd.DataFrame) -> pd.Series:
    return fixture_status_series(data)


def _has_stage_status(data: pd.DataFrame, stage: str, statuses: set[str]) -> bool:
    if data.empty:
        return False
    status = _status_series(data)
    return bool((data["stage_norm"].eq(stage) & status.isin(statuses)).any())


def _stage_completed(data: pd.DataFrame, stage: str) -> bool:
    if data.empty:
        return False
    stage_rows = data[data["stage_norm"].eq(stage)]
    if stage_rows.empty:
        return False
    status = _status_series(stage_rows)
    return bool(status.isin(COMPLETED_STATUSES).all())


def detect_current_tournament_phase(live_fixtures_df: pd.DataFrame, live_rounds_df: pd.DataFrame | None = None) -> dict:
    ensure_source_verification_directories()
    if live_fixtures_df is None or live_fixtures_df.empty:
        result = {
            "current_phase": "pre_group_stage",
            "completed_match_count": 0,
            "completed_group_match_count": 0,
            "completed_knockout_match_count": 0,
            "latest_completed_match_date": "",
            "next_scheduled_match_date": "",
            "current_phase_confidence": "low",
            "reason": "No live fixture rows were available.",
        }
        _write_report(result)
        return result

    data = live_fixtures_df.copy()
    data["stage_norm"] = data.get("stage", "").apply(normalize_stage_name)
    status = _status_series(data)
    completed_mask = status.isin(COMPLETED_STATUSES)
    live_mask = status.isin(LIVE_STATUSES)
    scheduled_mask = status.isin(SCHEDULED_STATUSES)
    group_mask = data["stage_norm"].eq("Group Stage")
    knockout_mask = data["stage_norm"].isin(["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final"])

    if _has_stage_status(data, "Final", COMPLETED_STATUSES):
        phase, reason = "complete", "Final is completed."
    elif _has_stage_status(data, "Final", LIVE_STATUSES) or _stage_completed(data, "Semifinal"):
        phase, reason = "final", "Final is live or semifinals are completed."
    elif _has_stage_status(data, "Semifinal", LIVE_STATUSES | COMPLETED_STATUSES) or _stage_completed(data, "Quarterfinal"):
        phase, reason = "semifinal", "Semifinals are present or quarterfinals are completed."
    elif _has_stage_status(data, "Quarterfinal", LIVE_STATUSES | COMPLETED_STATUSES) or _stage_completed(data, "Round of 16"):
        phase, reason = "quarterfinal", "Quarterfinals are present or Round of 16 is completed."
    elif _has_stage_status(data, "Round of 16", LIVE_STATUSES | COMPLETED_STATUSES) or _stage_completed(data, "Round of 32"):
        phase, reason = "round_of_16", "Round of 16 is present or Round of 32 is completed."
    elif _has_stage_status(data, "Round of 32", LIVE_STATUSES | COMPLETED_STATUSES) or _stage_completed(data, "Group Stage"):
        phase, reason = "round_of_32", "Round of 32 is present or group stage is completed."
    elif bool((group_mask & (completed_mask | live_mask)).any()):
        phase, reason = "group_stage", "At least one group match is completed or live."
    else:
        phase, reason = "pre_group_stage", "No completed/live tournament matches were detected."

    dates = pd.to_datetime(data.get("date", pd.Series(dtype=str)), errors="coerce", utc=True)
    latest_completed = dates[completed_mask].max()
    next_scheduled = dates[scheduled_mask & dates.notna()].min()
    result = {
        "current_phase": phase,
        "completed_match_count": int(completed_mask.sum()),
        "completed_group_match_count": int((completed_mask & group_mask).sum()),
        "completed_knockout_match_count": int((completed_mask & knockout_mask).sum()),
        "latest_completed_match_date": "" if pd.isna(latest_completed) else latest_completed.isoformat(),
        "next_scheduled_match_date": "" if pd.isna(next_scheduled) else next_scheduled.isoformat(),
        "current_phase_confidence": "high" if len(data) >= 100 else "medium" if len(data) else "low",
        "reason": reason,
    }
    _write_report(result)
    return result


def _write_report(result: dict) -> str:
    lines = [
        "# Current Phase Report",
        "",
        f"- Current phase: {result['current_phase']}",
        f"- Completed matches: {result['completed_match_count']}",
        f"- Completed group matches: {result['completed_group_match_count']}",
        f"- Completed knockout matches: {result['completed_knockout_match_count']}",
        f"- Latest completed match date: {result['latest_completed_match_date'] or 'none'}",
        f"- Next scheduled match date: {result['next_scheduled_match_date'] or 'unknown'}",
        f"- Confidence: {result['current_phase_confidence']}",
        f"- Reason: {result['reason']}",
    ]
    path = SOURCE_VERIFICATION_REPORT_DIR / "current_phase_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
