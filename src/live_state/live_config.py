"""Configuration for live tournament-state forecasting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import API_FOOTBALL_WORLD_CUP_LEAGUE_ID, OUTPUTS_DIR

LIVE_SEASON = 2026
DEFAULT_LIVE_N_SIMULATIONS = 10000
RANDOM_SEED = 42

# API-Football examples often use league=1 for FIFA World Cup. Prefer .env when set.
API_FOOTBALL_LEAGUE_ID = int(API_FOOTBALL_WORLD_CUP_LEAGUE_ID or 1)

LIVE_STATE_DIR = OUTPUTS_DIR / "live_state"
LIVE_REPORT_DIR = OUTPUTS_DIR / "reports" / "live_state"

TOURNAMENT_PHASES = [
    "pre_group_stage",
    "group_stage",
    "round_of_32",
    "round_of_16",
    "quarterfinal",
    "semifinal",
    "final",
    "complete",
]

STAGE_TO_PHASE = {
    "group stage": "group_stage",
    "round of 32": "round_of_32",
    "round of 16": "round_of_16",
    "quarterfinal": "quarterfinal",
    "quarterfinals": "quarterfinal",
    "semifinal": "semifinal",
    "semifinals": "semifinal",
    "final": "final",
}


def ensure_live_directories() -> None:
    LIVE_STATE_DIR.mkdir(parents=True, exist_ok=True)
    LIVE_REPORT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_stage_name(stage: object) -> str:
    text = str(stage or "").strip()
    lowered = text.lower()
    if "group" in lowered:
        return "Group Stage"
    if "round of 32" in lowered or "1/16" in lowered:
        return "Round of 32"
    if "round of 16" in lowered or "1/8" in lowered:
        return "Round of 16"
    if "quarter" in lowered:
        return "Quarterfinal"
    if "semi" in lowered:
        return "Semifinal"
    if "third" in lowered:
        return "Third Place Playoff"
    if "final" in lowered:
        return "Final"
    return text or "Unknown"


def coerce_bool_series(values, index=None) -> pd.Series:
    if isinstance(values, pd.Series):
        series = values
    else:
        series = pd.Series(values, index=index)
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    text = series.astype(str).str.strip().str.lower()
    return text.isin({"true", "1", "yes", "y", "t"})


def fixture_status_series(fixtures_df: pd.DataFrame) -> pd.Series:
    if fixtures_df is None or fixtures_df.empty:
        return pd.Series(dtype=str)
    if "status" in fixtures_df:
        status = fixtures_df["status"].astype(str).str.strip().str.lower()
    elif "status_short" in fixtures_df:
        status = fixtures_df["status_short"].astype(str).str.strip().str.lower()
    elif "status_long" in fixtures_df:
        status = fixtures_df["status_long"].astype(str).str.strip().str.lower()
    else:
        status = pd.Series("", index=fixtures_df.index, dtype=str)
    if "is_completed" in fixtures_df:
        status = status.mask(coerce_bool_series(fixtures_df["is_completed"]), "completed")
    if "is_live" in fixtures_df:
        status = status.mask(coerce_bool_series(fixtures_df["is_live"]), "live")
    if "is_scheduled" in fixtures_df:
        status = status.mask(coerce_bool_series(fixtures_df["is_scheduled"]) & status.eq(""), "scheduled")
    return status


def detect_current_phase(fixtures_df) -> str:
    if fixtures_df is None or fixtures_df.empty:
        return "pre_group_stage"
    data = fixtures_df.copy()
    stage = data["stage"] if "stage" in data else pd.Series("", index=data.index)
    data["stage_norm"] = stage.apply(normalize_stage_name)
    data["status_norm"] = fixture_status_series(data)
    completed = data[data["status_norm"].isin(["completed", "finished", "ft", "match finished", "aet", "pen"])]
    live_or_completed = data[data["status_norm"].isin(["completed", "finished", "ft", "match finished", "aet", "pen", "live", "in progress", "1h", "2h", "ht", "et"])]
    if completed["stage_norm"].eq("Final").any():
        return "complete"
    for stage, phase in [
        ("Final", "final"),
        ("Semifinal", "semifinal"),
        ("Quarterfinal", "quarterfinal"),
        ("Round of 16", "round_of_16"),
        ("Round of 32", "round_of_32"),
    ]:
        if live_or_completed["stage_norm"].eq(stage).any():
            return phase
    if len(completed) == 0:
        return "pre_group_stage"
    return "group_stage"


def phase_prediction_status(phase: str) -> str:
    if phase == "complete":
        return "tournament_complete"
    if phase == "final":
        return "finalists_known"
    return "finalist_prediction_active"
