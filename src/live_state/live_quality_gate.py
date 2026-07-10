"""Quality gate that prevents fallback forecasts from being mislabeled live."""

from __future__ import annotations

import json

import pandas as pd
from pandas.errors import EmptyDataError

from src.live_state.current_phase_detector import detect_current_tournament_phase
from src.live_state.live_config import LIVE_STATE_DIR, coerce_bool_series
from src.live_state.live_source_config import PUBLIC_LABELS, SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories


def _read_csv(path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except EmptyDataError:
        return pd.DataFrame()


def _coverage(value: bool) -> float:
    return 1.0 if value else 0.0


def evaluate_live_forecast_quality(
    live_fixtures: pd.DataFrame | None = None,
    live_standings: pd.DataFrame | None = None,
    live_bracket: pd.DataFrame | None = None,
    current_phase: str | None = None,
) -> dict:
    ensure_source_verification_directories()
    fixtures = live_fixtures if live_fixtures is not None else _read_csv(LIVE_STATE_DIR / "live_fixtures_normalized.csv")
    standings = live_standings if live_standings is not None else _read_csv(LIVE_STATE_DIR / "live_standings_normalized.csv")
    bracket = live_bracket if live_bracket is not None else _read_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
    phase_info = detect_current_tournament_phase(fixtures)
    phase = current_phase or phase_info["current_phase"]

    fixture_sources = fixtures.get("source", pd.Series(dtype=str)).astype(str).str.lower() if not fixtures.empty else pd.Series(dtype=str)
    provider_series = fixtures.get("provider", pd.Series("", index=fixtures.index)).astype(str).str.lower() if not fixtures.empty else pd.Series(dtype=str)
    live_fixture_rows = int((fixture_sources.isin(["api_football", "official_fifa", "football_data_org"]) | provider_series.eq("football_data_org")).sum()) if not fixtures.empty else 0
    football_data_rows = int((fixture_sources.eq("football_data_org") | provider_series.eq("football_data_org")).sum()) if not fixtures.empty else 0
    football_data_has_last_updated = bool(football_data_rows and fixtures.get("last_updated", pd.Series(dtype=str)).notna().any())
    live_fixtures_available = live_fixture_rows > 0
    completed_count = int(coerce_bool_series(fixtures["is_completed"]).sum()) if not fixtures.empty and "is_completed" in fixtures else phase_info["completed_match_count"]
    live_count = int(coerce_bool_series(fixtures["is_live"]).sum()) if not fixtures.empty and "is_live" in fixtures else 0
    standings_source = standings.get("source", pd.Series(dtype=str)).astype(str).str.lower() if not standings.empty else pd.Series(dtype=str)
    standings_provider = standings.get("provider", pd.Series("", index=standings.index)).astype(str).str.lower() if not standings.empty else pd.Series(dtype=str)
    api_standings_available = bool(standings_source.isin(["api_football", "football_data_org"]).any() or standings_provider.eq("football_data_org").any())
    computed_standings_available = bool(standings_source.isin(["computed_from_completed_matches", "computed_from_football_data_org_matches"]).any()) or (not standings.empty and completed_count > 0)
    standings_available = api_standings_available or computed_standings_available
    bracket_sources = bracket.get("bracket_source", pd.Series(dtype=str)).astype(str).str.lower() if not bracket.empty else pd.Series(dtype=str)
    fallback_usage_rate = float(bracket_sources.eq("fallback_template").mean()) if not bracket_sources.empty else 1.0
    bracket_live_coverage = float(bracket_sources.isin(["live_api", "official_fifa", "computed_from_group_results", "football_data_org_live"]).mean()) if not bracket_sources.empty else 0.0

    if fixtures.empty or not live_fixtures_available:
        if fixtures.empty:
            mode = "insufficient_data"
        elif completed_count == 0 and phase == "pre_group_stage":
            mode = "fallback_pre_tournament_forecast"
        else:
            mode = "partially_live_forecast"
    elif completed_count > 0 or phase != "pre_group_stage" or live_count > 0:
        if standings_available and (fallback_usage_rate < 0.5 or phase in {"pre_group_stage", "group_stage"}):
            mode = "true_live_forecast"
        else:
            mode = "partially_live_forecast"
    elif completed_count == 0 and phase == "pre_group_stage" and fallback_usage_rate >= 0.5:
        mode = "fallback_pre_tournament_forecast"
    else:
        mode = "partially_live_forecast"

    live_fixture_coverage = live_fixture_rows / len(fixtures) if len(fixtures) else 0.0
    completed_result_coverage = _coverage(completed_count > 0 or phase != "pre_group_stage")
    standings_coverage = _coverage(standings_available)
    source_quality_score = round(
        35 * live_fixture_coverage
        + 25 * completed_result_coverage
        + 20 * standings_coverage
        + 20 * bracket_live_coverage
    )
    if football_data_rows > 0:
        source_quality_score += 20
    if football_data_rows > 0 and (completed_count > 0 or live_count > 0):
        source_quality_score += 15
    if football_data_rows > 0 and standings_available:
        source_quality_score += 15
    if football_data_rows > 0 and bracket_live_coverage > 0:
        source_quality_score += 10
    if football_data_has_last_updated:
        source_quality_score += 5
    if mode == "fallback_pre_tournament_forecast":
        source_quality_score = min(source_quality_score, 35)
    if mode == "insufficient_data":
        source_quality_score = min(source_quality_score, 20)
    source_quality_score = min(source_quality_score, 100)
    finalist_allowed = mode in {"true_live_forecast", "partially_live_forecast"}
    champion_allowed = finalist_allowed
    result = {
        "forecast_mode": mode,
        "source_quality_score": int(source_quality_score),
        "source_quality_level": "high" if source_quality_score >= 80 else "medium" if source_quality_score >= 50 else "low" if source_quality_score >= 20 else "invalid",
        "live_fixture_coverage": round(live_fixture_coverage, 4),
        "completed_result_coverage": round(completed_result_coverage, 4),
        "standings_coverage": round(standings_coverage, 4),
        "bracket_live_coverage": round(bracket_live_coverage, 4),
        "fallback_usage_rate": round(fallback_usage_rate, 4),
        "finalist_prediction_allowed": finalist_allowed,
        "champion_prediction_allowed": champion_allowed,
        "current_phase": phase,
        "completed_result_count": completed_count,
        "live_match_count": live_count,
        "fixture_rows": len(fixtures),
        "live_fixture_rows": live_fixture_rows,
        "football_data_org_fixture_rows": football_data_rows,
        "standings_rows": len(standings),
        "bracket_rows": len(bracket),
        "public_label": PUBLIC_LABELS[mode],
        "reason": _reason(mode, live_fixtures_available, completed_count, standings_available, fallback_usage_rate, phase),
    }
    json_path = LIVE_STATE_DIR / "live_forecast_quality_gate.json"
    md_path = SOURCE_VERIFICATION_REPORT_DIR / "live_forecast_quality_gate.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# Live Forecast Quality Gate",
        "",
        f"FORECAST_MODE = {result['forecast_mode']}",
        "",
        f"- Public label: {result['public_label']}",
        f"- Source quality score: {result['source_quality_score']}",
        f"- Source quality level: {result['source_quality_level']}",
        f"- Current phase: {result['current_phase']}",
        f"- Completed result count: {result['completed_result_count']}",
        f"- Live fixture coverage: {result['live_fixture_coverage']:.2%}",
        f"- Completed result coverage: {result['completed_result_coverage']:.2%}",
        f"- Standings coverage: {result['standings_coverage']:.2%}",
        f"- Bracket live coverage: {result['bracket_live_coverage']:.2%}",
        f"- Fallback usage rate: {result['fallback_usage_rate']:.2%}",
        f"- Finalist prediction allowed by default: {'yes' if finalist_allowed else 'no'}",
        f"- Champion prediction allowed by default: {'yes' if champion_allowed else 'no'}",
        f"- Reason: {result['reason']}",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    result.update({"json": str(json_path), "report": str(md_path)})
    return result


def _reason(mode: str, live_fixtures_available: bool, completed_count: int, standings_available: bool, fallback_usage: float, phase: str) -> str:
    if mode == "true_live_forecast":
        return "Live fixture/results source is available and current-state requirements are satisfied."
    if mode == "partially_live_forecast":
        return "Some live current-state data is available, but standings or bracket coverage still relies on fallback/computed assumptions."
    if mode == "fallback_pre_tournament_forecast":
        return "No completed 2026 results were detected, phase is pre_group_stage, and fallback bracket usage is high."
    missing = []
    if not live_fixtures_available:
        missing.append("live fixtures")
    if not standings_available:
        missing.append("standings")
    if fallback_usage >= 1.0:
        missing.append("live bracket")
    return f"Missing reliable {', '.join(missing) or 'live state'} for phase {phase}."
