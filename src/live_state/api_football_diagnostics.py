"""Deep API-Football diagnostics for true-live forecast gating."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.config import API_FOOTBALL_KEY, API_FOOTBALL_WORLD_CUP_LEAGUE_ID
from src.fetch.fetch_api_football import api_football_request
from src.live_state.api_football_live import normalize_live_fixture_response, normalize_live_standings_response
from src.live_state.current_phase_detector import detect_current_tournament_phase
from src.live_state.live_config import LIVE_SEASON, normalize_stage_name
from src.live_state.live_source_config import SOURCE_SNAPSHOT_DIR, SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories

SEARCH_TERMS = ["World Cup", "FIFA World Cup", "World", "World Championship"]


def _sanitize(payload: dict | Any) -> dict:
    if not isinstance(payload, dict):
        return {"response": payload}
    sanitized = dict(payload)
    sanitized.pop("parameters", None)
    return sanitized


def _write_snapshot(filename: str, payload: dict) -> str:
    ensure_source_verification_directories()
    path = SOURCE_SNAPSHOT_DIR / filename
    path.write_text(json.dumps(_sanitize(payload), indent=2), encoding="utf-8")
    return str(path)


def _safe_call(endpoint: str, params: dict[str, Any], filename: str) -> dict:
    if not API_FOOTBALL_KEY:
        payload = {"response": [], "errors": {"missing_key": "API_FOOTBALL_KEY is not set"}}
        _write_snapshot(filename, payload)
        return {"status": "missing_key", "payload": payload, "error": "API_FOOTBALL_KEY is not set"}
    try:
        payload = api_football_request(endpoint, params)
        _write_snapshot(filename, payload)
        errors = payload.get("errors")
        has_errors = bool(errors) and errors not in ({}, [])
        return {"status": "failed" if has_errors else "success", "payload": payload, "error": str(errors) if has_errors else ""}
    except Exception as exc:
        payload = {"response": [], "errors": {"request_failed": str(exc)}}
        _write_snapshot(filename, payload)
        return {"status": "failed", "payload": payload, "error": str(exc)}


def _candidate_score(name: str, country: str, league_type: str, fixture_count: int) -> int:
    lower = str(name).lower()
    score = 0
    if "fifa world cup" in lower:
        score += 60
    elif "world cup" in lower:
        score += 45
    elif "world" in lower:
        score += 20
    if str(country).lower() == "world":
        score += 15
    if str(league_type).lower() in {"cup", "league"}:
        score += 5
    if fixture_count == 104:
        score += 30
    elif 90 <= fixture_count <= 110:
        score += 20
    elif fixture_count > 0:
        score += 8
    return score


def verify_world_cup_2026_league_id() -> dict:
    ensure_source_verification_directories()
    candidates: dict[int, dict] = {}
    problems = []
    configured_id = int(API_FOOTBALL_WORLD_CUP_LEAGUE_ID) if API_FOOTBALL_WORLD_CUP_LEAGUE_ID else None
    if configured_id:
        candidates[configured_id] = {
            "league_id": configured_id,
            "league_name": "configured in .env",
            "country": "",
            "season": LIVE_SEASON,
            "type": "",
            "fixture_count": 0,
            "confidence_score": 0,
            "reason": "API_FOOTBALL_WORLD_CUP_LEAGUE_ID is set",
        }
    if not API_FOOTBALL_KEY:
        problems.append("API_FOOTBALL_KEY is missing; league search could not run.")
    else:
        for term in SEARCH_TERMS:
            result = _safe_call("leagues", {"search": term, "season": LIVE_SEASON}, f"api_football_leagues_{term.lower().replace(' ', '_')}.json")
            for item in result["payload"].get("response", []):
                league = item.get("league", {})
                country = item.get("country", {})
                seasons = item.get("seasons", []) or [{"year": LIVE_SEASON}]
                if not any(int(season.get("year") or 0) == LIVE_SEASON for season in seasons):
                    continue
                league_id = league.get("id")
                if league_id is None:
                    continue
                candidates.setdefault(
                    int(league_id),
                    {
                        "league_id": int(league_id),
                        "league_name": league.get("name", ""),
                        "country": country.get("name", ""),
                        "season": LIVE_SEASON,
                        "type": league.get("type", ""),
                        "fixture_count": 0,
                        "confidence_score": 0,
                        "reason": f"matched search term `{term}`",
                    },
                )
    for league_id, row in candidates.items():
        if API_FOOTBALL_KEY:
            fixtures = _safe_call("fixtures", {"league": league_id, "season": LIVE_SEASON}, f"api_football_league_{league_id}_fixture_probe.json")
            row["fixture_count"] = len(fixtures["payload"].get("response", []))
            if fixtures["status"] != "success":
                row["reason"] = f"{row['reason']}; fixture probe failed"
        row["confidence_score"] = _candidate_score(row["league_name"], row["country"], row["type"], int(row["fixture_count"]))
    df = pd.DataFrame(candidates.values())
    if df.empty:
        df = pd.DataFrame(columns=["league_id", "league_name", "country", "season", "type", "fixture_count", "confidence_score", "reason"])
    df = df.sort_values(["confidence_score", "fixture_count"], ascending=[False, False])
    csv_path = SOURCE_VERIFICATION_REPORT_DIR / "world_cup_league_candidates.csv"
    df.to_csv(csv_path, index=False)
    selected = int(df.iloc[0]["league_id"]) if not df.empty and int(df.iloc[0].get("fixture_count", 0)) > 0 else configured_id or 1
    configured_row = df[df["league_id"].eq(configured_id)] if configured_id and not df.empty else pd.DataFrame()
    recommended = ""
    if configured_id and not configured_row.empty and int(configured_row.iloc[0]["fixture_count"]) == 0:
        better = df[df["fixture_count"].gt(0)] if "fixture_count" in df else pd.DataFrame()
        if not better.empty:
            recommended = f"Configured league ID returned 0 fixtures. Consider setting API_FOOTBALL_WORLD_CUP_LEAGUE_ID={int(better.iloc[0]['league_id'])}."
    if not recommended and not df.empty and int(df.iloc[0].get("fixture_count", 0)) == 0:
        recommended = "No candidate returned real fixtures; use fallback/insufficient-data mode and check API plan/data availability."
    elif not recommended:
        recommended = f"Use league ID {selected} for World Cup 2026 live checks."
    report_path = SOURCE_VERIFICATION_REPORT_DIR / "world_cup_league_id_verification.md"
    lines = [
        "# World Cup 2026 League ID Verification",
        "",
        f"- API key found: {'yes' if API_FOOTBALL_KEY else 'no'}",
        f"- Configured league ID: {configured_id or 'not set'}",
        f"- Selected league ID: {selected}",
        f"- Recommendation: {recommended}",
        "",
        "| League ID | Name | Country | Type | Fixture count | Confidence | Reason |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for _, row in df.iterrows():
        lines.append(f"| {row['league_id']} | {row['league_name']} | {row['country']} | {row['type']} | {row['fixture_count']} | {row['confidence_score']} | {row['reason']} |")
    if problems:
        lines.extend(["", "## Problems", ""])
        lines.extend(f"- {problem}" for problem in problems)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {"selected_league_id": selected, "configured_league_id": configured_id, "candidates": df, "report": str(report_path), "csv": str(csv_path), "recommendation": recommended}


def run_api_football_live_diagnostics() -> dict:
    ensure_source_verification_directories()
    verification = verify_world_cup_2026_league_id()
    league_id = verification["selected_league_id"]
    fixtures_result = _safe_call("fixtures", {"league": league_id, "season": LIVE_SEASON}, "api_football_fixtures_diagnostic.json")
    rounds_result = _safe_call("fixtures/rounds", {"league": league_id, "season": LIVE_SEASON}, "api_football_rounds_diagnostic.json")
    standings_result = _safe_call("standings", {"league": league_id, "season": LIVE_SEASON}, "api_football_standings_diagnostic.json")
    teams_result = _safe_call("teams", {"league": league_id, "season": LIVE_SEASON}, "api_football_teams_diagnostic.json")
    fixtures = normalize_live_fixture_response(fixtures_result["payload"])
    standings = normalize_live_standings_response(standings_result["payload"])
    phase = detect_current_tournament_phase(fixtures)
    completed = int(fixtures.get("is_completed", pd.Series(dtype=bool)).astype(bool).sum()) if not fixtures.empty else 0
    live = int(fixtures.get("is_live", pd.Series(dtype=bool)).astype(bool).sum()) if not fixtures.empty else 0
    scheduled = int(fixtures.get("is_scheduled", pd.Series(dtype=bool)).astype(bool).sum()) if not fixtures.empty else 0
    rounds = rounds_result["payload"].get("response", []) if isinstance(rounds_result["payload"], dict) else []
    report_path = SOURCE_VERIFICATION_REPORT_DIR / "api_football_live_diagnostic.md"
    problems = []
    if fixtures_result["status"] != "success":
        problems.append(f"Fixtures endpoint failed: {fixtures_result['error']}")
    if fixtures.empty:
        problems.append("Fixtures endpoint returned 0 normalized rows.")
    if standings.empty:
        problems.append("Standings endpoint returned 0 normalized rows.")
    if completed == 0:
        problems.append("No completed FIFA 2026 matches detected from API-Football.")
    next_action = "Run the quality gate. If mode is fallback_pre_tournament_forecast, only run forecast with --allow-fallback-forecast for testing." if problems else "Live source looks usable; run live-quality-gate and then run-live-forecast."
    lines = [
        "# API-Football Live Diagnostic",
        "",
        f"- API key found: {'yes' if API_FOOTBALL_KEY else 'no'}",
        f"- League ID used: {league_id}",
        f"- Season used: {LIVE_SEASON}",
        f"- Fixtures endpoint status: {fixtures_result['status']}",
        f"- Fixtures row count: {len(fixtures)}",
        f"- Completed matches: {completed}",
        f"- Live matches: {live}",
        f"- Scheduled matches: {scheduled}",
        f"- Rounds endpoint status: {rounds_result['status']}",
        f"- Available rounds: {', '.join(str(round) for round in rounds[:30]) if rounds else 'none'}",
        f"- Standings endpoint status: {standings_result['status']}",
        f"- Standings row count: {len(standings)}",
        f"- Teams endpoint status: {teams_result['status']}",
        f"- Teams row count: {len(teams_result['payload'].get('response', [])) if isinstance(teams_result['payload'], dict) else 0}",
        f"- Detected current phase: {phase['current_phase']}",
        "",
        "## Problems Found",
        "",
    ]
    lines.extend(f"- {problem}" for problem in problems) if problems else lines.append("- None")
    lines.extend(["", "## Exact Next Action", "", next_action, "", "No API secrets are printed or saved."])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "status": "success" if fixtures_result["status"] == "success" else "failed",
        "league_id": league_id,
        "fixtures_count": len(fixtures),
        "completed_count": completed,
        "live_count": live,
        "scheduled_count": scheduled,
        "standings_count": len(standings),
        "rounds_count": len(rounds),
        "current_phase": phase["current_phase"],
        "report": str(report_path),
        "league_report": verification["report"],
    }

