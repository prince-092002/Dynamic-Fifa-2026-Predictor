"""Provider diagnostics for live-state data sources."""

from __future__ import annotations

import json

import pandas as pd

from src.live_state.live_config import LIVE_STATE_DIR
from src.live_state.providers.football_data_org_provider import FootballDataOrgProvider, SNAPSHOT_DIR


def diagnose_football_data_org() -> dict:
    provider = FootballDataOrgProvider()
    return provider.diagnose()


def fetch_football_data_org() -> dict:
    provider = FootballDataOrgProvider()
    competition = provider.fetch_competition(use_id=False)
    matches = provider.fetch_matches(use_id=False)
    teams = provider.fetch_teams(use_id=False)
    standings = provider.fetch_standings(use_id=False)
    return {"competition": competition, "matches": matches, "teams": teams, "standings": standings}


def normalize_football_data_org() -> dict:
    provider = FootballDataOrgProvider()
    matches = provider.fetch_matches(use_id=False)
    teams = provider.fetch_teams(use_id=False)
    standings = provider.fetch_standings(use_id=False)
    fixtures_df = provider.normalize_fixtures(matches)
    teams_df = provider.normalize_teams(teams)
    standings_df = provider.normalize_standings(standings)
    if standings_df.empty:
        standings_df = provider.compute_standings_from_completed_matches(fixtures_df)
    bracket_df = provider.normalize_bracket(fixtures_df)
    used_snapshot = False
    if fixtures_df.empty:
        snapshot_matches = _read_snapshot("football_data_org_matches_2026.json")
        if snapshot_matches.get("matches"):
            snapshot_teams = _read_snapshot("football_data_org_teams_2026.json")
            snapshot_standings = _read_snapshot("football_data_org_standings_2026.json")
            fixtures_df = provider.normalize_fixtures(snapshot_matches)
            teams_df = provider.normalize_teams(snapshot_teams)
            standings_df = provider.normalize_standings(snapshot_standings)
            if standings_df.empty:
                standings_df = provider.compute_standings_from_completed_matches(fixtures_df)
            bracket_df = provider.normalize_bracket(fixtures_df)
            used_snapshot = True
    provider._save_normalized(fixtures_df, teams_df, standings_df, bracket_df)
    used_cached = False
    if fixtures_df.empty:
        cached_fixtures = _read_normalized("football_data_org_fixtures_normalized.csv")
        if not cached_fixtures.empty:
            fixtures_df = cached_fixtures
            teams_df = _read_normalized("football_data_org_teams_normalized.csv")
            standings_df = _read_normalized("football_data_org_standings_normalized.csv")
            bracket_df = _read_normalized("football_data_org_bracket_normalized.csv")
            used_cached = True
    summary = provider.source_quality_summary(fixtures_df, teams_df, standings_df, bracket_df)
    summary["used_cached_normalized_data"] = used_cached
    summary["used_saved_snapshot_data"] = used_snapshot
    if used_cached:
        summary["limitations"].append("Latest football-data.org normalization request returned no usable rows; using previously saved normalized provider data.")
    if used_snapshot:
        summary["limitations"].append("Latest football-data.org normalization request returned no usable rows; rebuilt normalized data from saved sanitized provider snapshot.")
    report = provider._write_report(summary, fixtures_df, teams_df, standings_df)
    return {"fixtures": fixtures_df, "teams": teams_df, "standings": standings_df, "bracket": bracket_df, "summary": summary, "report": report}


def _read_normalized(filename: str) -> pd.DataFrame:
    path = LIVE_STATE_DIR / filename
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _read_snapshot(filename: str) -> dict:
    path = SNAPSHOT_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}
