"""API-Football live-state fetch and normalization helpers."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.config import API_FOOTBALL_KEY
from src.fetch.fetch_api_football import BASE_URL, api_football_request, normalize_api_status
from src.live_state.live_config import API_FOOTBALL_LEAGUE_ID, LIVE_REPORT_DIR, LIVE_SEASON, LIVE_STATE_DIR, ensure_live_directories, normalize_stage_name
from src.live_state.live_source_config import SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories
from src.utils.dates import now_utc_iso


def _write_json(path, payload: dict, allow_empty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    response = payload.get("response", []) if isinstance(payload, dict) else []
    if response or allow_empty or not path.exists():
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _safe_api_call(endpoint: str, params: dict[str, Any], output_name: str) -> dict:
    ensure_live_directories()
    path = LIVE_STATE_DIR / output_name
    if not API_FOOTBALL_KEY:
        payload = {"response": [], "errors": {"missing_key": "API_FOOTBALL_KEY is not set"}, "source": "api_football"}
        _write_json(path, payload, allow_empty=not path.exists())
        return payload
    try:
        payload = api_football_request(endpoint, params)
        _write_json(path, payload, allow_empty=False)
        return payload
    except Exception as exc:
        payload = {"response": [], "errors": {"request_failed": str(exc)}, "source": "api_football"}
        _write_json(path, payload, allow_empty=not path.exists())
        return payload


def fetch_live_fixtures() -> dict:
    payload = _safe_api_call("fixtures", {"league": API_FOOTBALL_LEAGUE_ID, "season": LIVE_SEASON}, "api_football_live_fixtures.json")
    fixtures = normalize_live_fixture_response(payload)
    fixtures.to_csv(LIVE_STATE_DIR / "live_fixtures_normalized.csv", index=False)
    _write_fixture_status_report(fixtures)
    return payload


def fetch_live_rounds() -> dict:
    payload = _safe_api_call("fixtures/rounds", {"league": API_FOOTBALL_LEAGUE_ID, "season": LIVE_SEASON}, "api_football_live_rounds.json")
    rounds = normalize_live_rounds_response(payload)
    rounds.to_csv(LIVE_STATE_DIR / "live_rounds.csv", index=False)
    _write_rounds_report(rounds)
    return payload


def fetch_live_standings() -> dict:
    payload = _safe_api_call("standings", {"league": API_FOOTBALL_LEAGUE_ID, "season": LIVE_SEASON}, "api_football_live_standings.json")
    standings = normalize_live_standings_response(payload)
    standings.to_csv(LIVE_STATE_DIR / "live_standings_normalized.csv", index=False)
    _write_standings_report(standings, source="api" if not standings.empty else "unavailable", completed_group_matches=0)
    return payload


def fetch_live_teams() -> dict:
    return _safe_api_call("teams", {"league": API_FOOTBALL_LEAGUE_ID, "season": LIVE_SEASON}, "api_football_live_teams.json")


def fetch_live_bracket_or_knockout() -> dict:
    payload = fetch_live_fixtures()
    fixtures = normalize_live_fixture_response(payload)
    knockout = fixtures[~fixtures["stage"].eq("Group Stage")] if not fixtures.empty else fixtures
    report = LIVE_REPORT_DIR / "api_football_bracket_status.md"
    if knockout.empty:
        report.write_text(
            "# API-Football Bracket Status\n\nNo explicit/current knockout fixture rows were available. Fallback structure may be needed for unresolved future rounds.\n",
            encoding="utf-8",
        )
    else:
        report.write_text(
            f"# API-Football Bracket Status\n\nFound {len(knockout)} non-group fixture rows that can be used as live bracket state where teams are known.\n",
            encoding="utf-8",
        )
    return {"status": "success" if not knockout.empty else "unavailable", "rows": len(knockout), "report": str(report)}


def normalize_live_fixture_response(payload: dict) -> pd.DataFrame:
    rows = []
    for item in payload.get("response", []) if isinstance(payload, dict) else []:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        score = item.get("score", {})
        venue = fixture.get("venue", {})
        status_obj = fixture.get("status", {})
        status_short = status_obj.get("short")
        status_long = status_obj.get("long")
        status = normalize_api_status(status_short or status_long)
        home = teams.get("home", {})
        away = teams.get("away", {})
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        penalty = score.get("penalty") or {}
        stage = normalize_stage_name(league.get("round"))
        winner = ""
        if home.get("winner") is True:
            winner = home.get("name")
        elif away.get("winner") is True:
            winner = away.get("name")
        if pd.notna(home_goals) and pd.notna(away_goals) and home_goals is not None and away_goals is not None:
            winner = winner or (home.get("name") if home_goals > away_goals else away.get("name") if away_goals > home_goals else "Draw")
        rows.append(
            {
                "fixture_id": fixture.get("id"),
                "match_id": fixture.get("id"),
                "date": fixture.get("date"),
                "round": league.get("round"),
                "stage": stage,
                "group": league.get("round") if "group" in str(league.get("round", "")).lower() else "",
                "team_a": home.get("name"),
                "team_b": away.get("name"),
                "team_a_id": home.get("id"),
                "team_b_id": away.get("id"),
                "team_a_goals": home_goals,
                "team_b_goals": away_goals,
                "team_a_penalty_goals": penalty.get("home"),
                "team_b_penalty_goals": penalty.get("away"),
                "status": status,
                "status_short": status_short,
                "status_long": status_long,
                "elapsed": status_obj.get("elapsed"),
                "venue": venue.get("name"),
                "city": venue.get("city"),
                "country": "Canada/Mexico/United States",
                "winner": winner,
                "is_completed": status == "completed",
                "is_live": status == "live",
                "is_scheduled": status == "scheduled",
                "is_knockout": stage in {"Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Third Place Playoff"},
                "source": "api_football",
                "last_updated": now_utc_iso(),
            }
        )
    return pd.DataFrame(rows)


def normalize_live_rounds_response(payload: dict) -> pd.DataFrame:
    rows = []
    for idx, round_name in enumerate(payload.get("response", []) if isinstance(payload, dict) else [], start=1):
        stage = normalize_stage_name(round_name)
        rows.append(
            {
                "round_name": round_name,
                "normalized_stage": stage,
                "round_order": idx,
                "is_group_stage": stage == "Group Stage",
                "is_knockout": stage in {"Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Third Place Playoff"},
                "source": "api_football",
                "last_updated": now_utc_iso(),
            }
        )
    return pd.DataFrame(rows)


def normalize_live_standings_response(payload: dict) -> pd.DataFrame:
    rows = []
    for league_item in payload.get("response", []) if isinstance(payload, dict) else []:
        league = league_item.get("league", {})
        for group_rows in league.get("standings", []) or []:
            for row in group_rows:
                all_stats = row.get("all", {})
                goals = all_stats.get("goals", {})
                team = row.get("team", {})
                rows.append(
                    {
                        "group": row.get("group") or league.get("name"),
                        "rank": row.get("rank"),
                        "team": team.get("name"),
                        "played": all_stats.get("played"),
                        "wins": all_stats.get("win"),
                        "draws": all_stats.get("draw"),
                        "losses": all_stats.get("lose"),
                        "goals_for": goals.get("for"),
                        "goals_against": goals.get("against"),
                        "goal_difference": row.get("goalsDiff"),
                        "points": row.get("points"),
                        "form": row.get("form"),
                        "status": row.get("status"),
                        "description": row.get("description"),
                        "qualification_status": row.get("description") or "unknown",
                        "team_id": team.get("id"),
                        "source": "api_football",
                        "last_updated": now_utc_iso(),
                    }
                )
    return pd.DataFrame(rows)


def _write_fixture_status_report(fixtures: pd.DataFrame) -> str:
    ensure_source_verification_directories()
    path = SOURCE_VERIFICATION_REPORT_DIR / "live_fixture_status_report.md"
    if fixtures.empty:
        lines = ["# Live Fixture Status Report", "", "- Total fixtures: 0", "- Status: unavailable"]
    else:
        status = fixtures.get("status", pd.Series(dtype=str)).astype(str)
        dates = pd.to_datetime(fixtures.get("date", pd.Series(dtype=str)), errors="coerce", utc=True)
        rounds = fixtures.get("round", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
        lines = [
            "# Live Fixture Status Report",
            "",
            f"- Total fixtures: {len(fixtures)}",
            f"- Completed fixtures: {int(status.eq('completed').sum())}",
            f"- Live fixtures: {int(status.eq('live').sum())}",
            f"- Scheduled fixtures: {int(status.eq('scheduled').sum())}",
            f"- Cancelled/postponed fixtures: {int(status.isin(['cancelled', 'postponed']).sum())}",
            f"- Unknown statuses: {int(status.eq('unknown').sum())}",
            f"- Rounds detected: {', '.join(rounds) if rounds else 'none'}",
            f"- Earliest fixture date: {dates.min().isoformat() if dates.notna().any() else 'unknown'}",
            f"- Latest fixture date: {dates.max().isoformat() if dates.notna().any() else 'unknown'}",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _write_rounds_report(rounds: pd.DataFrame) -> str:
    ensure_source_verification_directories()
    path = SOURCE_VERIFICATION_REPORT_DIR / "live_rounds_report.md"
    lines = [
        "# Live Rounds Report",
        "",
        f"- Round rows: {len(rounds)}",
        f"- Group-stage rows: {int(rounds.get('is_group_stage', pd.Series(dtype=bool)).astype(bool).sum()) if not rounds.empty else 0}",
        f"- Knockout rows: {int(rounds.get('is_knockout', pd.Series(dtype=bool)).astype(bool).sum()) if not rounds.empty else 0}",
        "",
        "| Order | Round | Normalized stage |",
        "|---:|---|---|",
    ]
    for _, row in rounds.iterrows():
        lines.append(f"| {row['round_order']} | {row['round_name']} | {row['normalized_stage']} |")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _write_standings_report(standings: pd.DataFrame, source: str, completed_group_matches: int) -> str:
    ensure_source_verification_directories()
    path = SOURCE_VERIFICATION_REPORT_DIR / "live_standings_report.md"
    lines = [
        "# Live Standings Report",
        "",
        f"- Source used: {source}",
        f"- Standings rows: {len(standings)}",
        f"- Groups found: {standings['group'].nunique() if not standings.empty and 'group' in standings else 0}",
        f"- Teams found: {standings['team'].nunique() if not standings.empty and 'team' in standings else 0}",
        f"- Completed group matches used: {completed_group_matches}",
        f"- Qualification status: {'available/approximate' if not standings.empty else 'unavailable'}",
    ]
    if standings.empty:
        lines.append("- Reason: API standings returned no normalized rows and no computed standings were supplied to this report.")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_fetch_status_report(fixtures_payload: dict, standings_payload: dict, teams_payload: dict) -> str:
    ensure_live_directories()
    path = LIVE_REPORT_DIR / "api_football_live_status.md"
    lines = [
        "# API-Football Live Status",
        "",
        f"- Base URL: {BASE_URL}",
        f"- League ID: {API_FOOTBALL_LEAGUE_ID}",
        f"- Season: {LIVE_SEASON}",
        f"- API key present: {'yes' if API_FOOTBALL_KEY else 'no'}",
        f"- Fixture rows: {len(fixtures_payload.get('response', [])) if isinstance(fixtures_payload, dict) else 0}",
        f"- Standings response rows: {len(standings_payload.get('response', [])) if isinstance(standings_payload, dict) else 0}",
        f"- Teams response rows: {len(teams_payload.get('response', [])) if isinstance(teams_payload, dict) else 0}",
        "",
        "No API secrets are printed in this report.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
