"""Build a current tournament state snapshot."""

from __future__ import annotations

import json

import pandas as pd

from src.config import PROCESSED_DIR, PROJECT_ROOT
from src.live_state.live_config import LIVE_STATE_DIR, detect_current_phase, ensure_live_directories, fixture_status_series
from src.simulation.tournament_structure import is_tbd_team
from src.utils.dates import now_utc_iso


def _read(path, columns=None) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns or [])


def _team_rows_from_fixtures(fixtures: pd.DataFrame) -> pd.DataFrame:
    teams = []
    for column in ["team_a", "team_b"]:
        if column in fixtures:
            teams.extend([team for team in fixtures[column].dropna().astype(str) if not is_tbd_team(team)])
    return pd.DataFrame({"team": sorted(set(teams))})


def build_current_tournament_state(live_fixtures_df: pd.DataFrame | None = None, live_standings_df: pd.DataFrame | None = None) -> dict:
    ensure_live_directories()
    fixtures = live_fixtures_df if live_fixtures_df is not None and not live_fixtures_df.empty else _read(PROCESSED_DIR / "fixtures_2026.csv")
    standings = live_standings_df if live_standings_df is not None else pd.DataFrame()
    ratings = _read(PROCESSED_DIR / "team_ratings.csv")
    phase = detect_current_phase(fixtures)
    teams = _team_rows_from_fixtures(fixtures)
    if teams.empty and not ratings.empty:
        teams = ratings[["team"]].dropna().drop_duplicates()
    rows = []
    status = fixture_status_series(fixtures)
    completed = fixtures[status.isin(["completed", "finished", "ft", "match finished", "aet", "pen"])] if not fixtures.empty else pd.DataFrame()
    scheduled = fixtures[status.isin(["scheduled", "timed", "not started", "ns", "tbd"])] if not fixtures.empty else pd.DataFrame()
    live = fixtures[status.isin(["live", "in progress", "1h", "2h", "ht", "et"])] if not fixtures.empty else pd.DataFrame()
    standing_map = {}
    if standings is not None and not standings.empty:
        standing_map = {row["team"]: row for _, row in standings.iterrows() if "team" in row}
    for team in teams["team"].dropna().astype(str):
        standing = standing_map.get(team, {})
        rows.append(
            {
                "team": team,
                "group": standing.get("group", ""),
                "current_status": "still_alive",
                "current_stage": phase,
                "matches_played": int(pd.to_numeric(standing.get("played", 0), errors="coerce") or 0),
                "points": int(pd.to_numeric(standing.get("points", 0), errors="coerce") or 0),
                "goal_difference": int(pd.to_numeric(standing.get("goal_difference", 0), errors="coerce") or 0),
                "qualified_stage": standing.get("qualification_status", "unknown"),
                "eliminated": False,
                "still_alive": True,
                "source": "live_state_builder",
                "last_updated": now_utc_iso(),
            }
        )
    state = pd.DataFrame(rows)
    csv_path = LIVE_STATE_DIR / "current_tournament_state.csv"
    json_path = LIVE_STATE_DIR / "current_tournament_state.json"
    state.to_csv(csv_path, index=False)
    payload = {
        "current_phase": phase,
        "completed_matches": len(completed),
        "scheduled_matches": len(scheduled),
        "live_matches": len(live),
        "teams": state.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"state": state, "current_phase": phase, "csv": str(csv_path), "json": str(json_path)}


def load_current_tournament_state() -> pd.DataFrame:
    return _read(PROJECT_ROOT / "outputs" / "live_state" / "current_tournament_state.csv")
