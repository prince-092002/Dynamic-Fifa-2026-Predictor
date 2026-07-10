"""End-to-end live finalist forecast pipeline."""

from __future__ import annotations

import json

import pandas as pd
from pandas.errors import EmptyDataError

from src.config import PROCESSED_DIR
from src.live_state.api_football_live import (
    _write_fixture_status_report,
    fetch_live_bracket_or_knockout,
    fetch_live_fixtures,
    fetch_live_rounds,
    fetch_live_standings,
    fetch_live_teams,
    normalize_live_fixture_response,
    normalize_live_rounds_response,
    normalize_live_standings_response,
    write_fetch_status_report,
)
from src.live_state.bracket_state import build_current_knockout_bracket, merge_live_bracket_with_fallback_template
from src.live_state.api_football_diagnostics import run_api_football_live_diagnostics, verify_world_cup_2026_league_id
from src.live_state.current_phase_detector import detect_current_tournament_phase
from src.live_state.fifa_live import fetch_fifa_official_bracket_state, fetch_fifa_official_match_state
from src.live_state.finalist_aggregation import aggregate_live_finalist_results
from src.live_state.finalist_simulator import get_remaining_match_probabilities, run_live_finalist_simulation
from src.live_state.live_config import DEFAULT_LIVE_N_SIMULATIONS, LIVE_STATE_DIR, detect_current_phase, ensure_live_directories, phase_prediction_status
from src.live_state.live_quality_gate import evaluate_live_forecast_quality
from src.live_state.live_reports import write_finalist_prediction_summary, write_live_state_summary, write_live_update_limitations
from src.live_state.live_validation import validate_live_forecast
from src.live_state.provider_registry import select_live_provider
from src.live_state.source_verification import verify_against_secondary_sources
from src.live_state.standings_builder import build_and_save_standings
from src.live_state.state_builder import build_current_tournament_state


def _read_live_csv(path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except EmptyDataError:
        return pd.DataFrame()


def fetch_live_state_data() -> dict:
    ensure_live_directories()
    provider_result = select_live_provider()
    if provider_result.get("provider") == "football_data_org":
        detail = provider_result.get("data", {})
        fixtures = detail.get("fixtures", pd.DataFrame())
        standings = detail.get("standings", pd.DataFrame())
        rounds = pd.DataFrame()
        if not fixtures.empty:
            fixtures.to_csv(LIVE_STATE_DIR / "live_fixtures_normalized.csv", index=False)
            standings.to_csv(LIVE_STATE_DIR / "live_standings_normalized.csv", index=False)
            rounds.to_csv(LIVE_STATE_DIR / "live_rounds.csv", index=False)
            return {"fixtures": fixtures, "standings": standings, "rounds": rounds, "provider": "football_data_org", "reports": [provider_result.get("report", "")]}
    fixtures_payload = fetch_live_fixtures()
    rounds_payload = fetch_live_rounds()
    standings_payload = fetch_live_standings()
    teams_payload = fetch_live_teams()
    bracket_status = fetch_live_bracket_or_knockout()
    fixtures = normalize_live_fixture_response(fixtures_payload)
    if fixtures.empty and (PROCESSED_DIR / "fixtures_2026.csv").exists():
        fixtures = pd.read_csv(PROCESSED_DIR / "fixtures_2026.csv")
        fixtures["fixture_id"] = fixtures.get("match_id")
        fixtures["is_completed"] = fixtures.get("status", "").astype(str).str.lower().eq("completed")
        fixtures["is_live"] = fixtures.get("status", "").astype(str).str.lower().eq("live")
        fixtures["is_scheduled"] = ~fixtures["is_completed"] & ~fixtures["is_live"]
        fixtures["source"] = fixtures.get("source", "processed_csv")
        fixtures["status_short"] = fixtures.get("status", "")
        fixtures["status_long"] = fixtures.get("status", "")
        fixtures["is_knockout"] = ~fixtures.get("stage", "").astype(str).str.lower().str.contains("group", na=False)
        _write_fixture_status_report(fixtures)
    standings = normalize_live_standings_response(standings_payload)
    rounds = normalize_live_rounds_response(rounds_payload)
    fixtures.to_csv(LIVE_STATE_DIR / "live_fixtures_normalized.csv", index=False)
    standings.to_csv(LIVE_STATE_DIR / "live_standings_normalized.csv", index=False)
    rounds.to_csv(LIVE_STATE_DIR / "live_rounds.csv", index=False)
    fetch_report = write_fetch_status_report(fixtures_payload, standings_payload, teams_payload)
    return {"fixtures": fixtures, "standings": standings, "rounds": rounds, "provider": "api_football_or_processed_fallback", "reports": [fetch_report, bracket_status.get("report", "")]}


def build_live_state() -> dict:
    ensure_live_directories()
    fixtures = _read_live_csv(LIVE_STATE_DIR / "live_fixtures_normalized.csv")
    standings = _read_live_csv(LIVE_STATE_DIR / "live_standings_normalized.csv")
    if fixtures.empty:
        fetched = fetch_live_state_data()
        fixtures = fetched["fixtures"]
        standings = fetched["standings"]
    standings_result = build_and_save_standings(fixtures, standings)
    state = build_current_tournament_state(fixtures, standings_result["standings"])
    live_bracket = build_current_knockout_bracket(fixtures)
    merged = merge_live_bracket_with_fallback_template(live_bracket)
    probabilities = get_remaining_match_probabilities(state["state"])
    phase = detect_current_tournament_phase(fixtures)["current_phase"]
    return {"current_phase": phase, "state": state, "standings": standings_result, "bracket": merged, "probabilities": probabilities}


def run_live_source_verification() -> dict:
    ensure_live_directories()
    diagnostics = run_api_football_live_diagnostics()
    league = verify_world_cup_2026_league_id()
    fetch_result = fetch_live_state_data()
    build_result = build_live_state()
    secondary = verify_against_secondary_sources()
    gate = evaluate_live_forecast_quality(fetch_result["fixtures"], build_result["standings"]["standings"], build_result["bracket"], build_result["current_phase"])
    return {
        "diagnostics": diagnostics,
        "league": league,
        "fetch": fetch_result,
        "build": build_result,
        "secondary": secondary,
        "quality_gate": gate,
    }


def run_live_matchup_prediction_step() -> dict:
    """Identify resolved knockout matchups, build features, and predict them with the selected model."""
    from src.live_state.live_matchup_predictor import run_live_knockout_prediction_flow

    try:
        return {"status": "success", **run_live_knockout_prediction_flow()}
    except Exception as exc:  # never block the forecast; the simulator keeps Elo fallback
        return {"status": "failed", "error": str(exc), "matchup_count": 0, "predicted_rows": 0, "failed_rows": 0}


def run_live_forecast_pipeline(n_simulations: int = DEFAULT_LIVE_N_SIMULATIONS, seed: int = 42, allow_fallback_forecast: bool = False, skip_live_matchup_predictions: bool = False) -> dict:
    from src.live_state.run_audit import new_run_id
    from src.utils.dates import now_utc_iso

    ensure_live_directories()
    run_id = new_run_id()
    run_started_at = now_utc_iso()
    reports = []
    fetch_result = fetch_live_state_data()
    reports.extend([report for report in fetch_result.get("reports", []) if report])
    reports.append(fetch_fifa_official_match_state()["report"])
    reports.append(fetch_fifa_official_bracket_state()["report"])
    state_result = build_live_state()
    phase = state_result["current_phase"]
    gate = evaluate_live_forecast_quality(fetch_result["fixtures"], state_result["standings"]["standings"], state_result["bracket"], phase)
    if gate["forecast_mode"] == "insufficient_data" or (gate["forecast_mode"] == "fallback_pre_tournament_forecast" and not allow_fallback_forecast):
        summary = {
            "status": "blocked_by_quality_gate",
            "forecast_ran": False,
            "forecast_mode": gate["forecast_mode"],
            "public_label": gate["public_label"],
            "current_phase": phase,
            "finalist_prediction_active": False,
            "top_finalist_pair": "",
            "top_finalist_pair_probability": 0.0,
            "top_champion": "",
            "top_champion_probability": 0.0,
            "fallback_bracket_usage": gate["fallback_usage_rate"],
            "source_quality_score": gate["source_quality_score"],
            "reason": "Forecast not run because current live state has no completed 2026 results and fallback usage is too high." if gate["forecast_mode"] == "fallback_pre_tournament_forecast" else gate["reason"],
        }
        (LIVE_STATE_DIR / "live_forecast_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        reports.extend([gate["report"], write_live_state_summary(phase), write_live_update_limitations(gate["fallback_usage_rate"], {})])
        return {**summary, "reports": reports}
    if skip_live_matchup_predictions:
        matchup_prediction = {"status": "skipped", "matchup_count": 0, "predicted_rows": 0, "failed_rows": 0}
    else:
        matchup_prediction = run_live_matchup_prediction_step()
        get_remaining_match_probabilities(state_result["state"])
    sim_result = run_live_finalist_simulation(n_simulations=n_simulations, seed=seed)
    aggregate = aggregate_live_finalist_results(sim_result["results"])
    validation = validate_live_forecast()
    from src.live_state.live_prediction_reports import validate_live_knockout_predictions, write_live_knockout_prediction_report

    reports.append(write_live_knockout_prediction_report())
    matchup_validation = validate_live_knockout_predictions()
    reports.append(matchup_validation["report"])
    from src.live_state.live_matchup_features import REMAINING_MATCHUPS_PATH
    from src.live_state.run_audit import (
        append_forecast_history,
        append_probability_source_history,
        record_phase_transition,
        write_probability_source_progression_report,
        write_run_manifest,
    )

    matchups = _read_live_csv(REMAINING_MATCHUPS_PATH)
    matchup_ids = matchups.get("match_id", pd.Series(dtype=str)).astype(str).tolist() if not matchups.empty else []
    transition = record_phase_transition(phase, int(gate.get("completed_result_count", 0)), matchup_ids)
    bracket = state_result["bracket"]
    fallback_usage = float((bracket.get("bracket_source", pd.Series(dtype=str)) == "fallback_template").mean()) if not bracket.empty else 0.0
    source_counts = sim_result.get("source_counts", {})
    live_model_uses = int(source_counts.get("live_model_exact", 0) + source_counts.get("live_model_reversed", 0))
    summary = aggregate["summary"]
    summary.update(
        {
            "status": "success" if validation["status"] == "pass" else "partial_success",
            "forecast_ran": True,
            "forecast_mode": gate["forecast_mode"],
            "public_label": gate["public_label"],
            "current_phase": phase,
            "finalist_prediction_active": phase_prediction_status(phase) == "finalist_prediction_active",
            "fallback_bracket_usage": fallback_usage,
            "source_quality_score": gate["source_quality_score"],
            "live_matchup_prediction_status": matchup_prediction.get("status", "unknown"),
            "live_matchups_predicted": matchup_prediction.get("predicted_rows", 0),
            "live_model_probability_uses": live_model_uses,
            "probability_source_counts": {k: int(v) for k, v in source_counts.items()},
        }
    )
    (LIVE_STATE_DIR / "live_forecast_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    append_probability_source_history(run_id, phase, n_simulations, len(matchup_ids), int(matchup_prediction.get("predicted_rows", 0)), source_counts)
    provider_name = "football_data_org" if gate.get("football_data_org_fixture_rows", 0) > 0 else "unknown"
    append_forecast_history(run_id, phase, n_simulations, provider_name, gate["forecast_mode"])
    reports.append(write_probability_source_progression_report())
    manifest_path = write_run_manifest(
        {
            "run_id": run_id,
            "run_started_at": run_started_at,
            "run_completed_at": now_utc_iso(),
            "provider": "football_data_org" if gate.get("football_data_org_fixture_rows", 0) > 0 else "unknown",
            "forecast_mode": gate["forecast_mode"],
            "source_quality_score": gate["source_quality_score"],
            "current_phase": phase,
            "simulation_count": n_simulations,
            "seed": seed,
            "selected_model": matchup_prediction.get("model_name", "unknown"),
            "known_live_knockout_matchups": len(matchup_ids),
            "live_model_predictions_generated": int(matchup_prediction.get("predicted_rows", 0)),
            "live_matchup_prediction_status": matchup_prediction.get("status", "unknown"),
            "live_forecast_validation": validation["status"],
            "live_knockout_prediction_validation": matchup_validation["status"],
            "phase_transition": {k: transition[k] for k in ["previous_phase", "current_phase", "phase_changed", "newly_resolved_matchups", "newly_completed_matches"]},
            "top_finalist_pair": summary.get("top_finalist_pair", ""),
            "top_champion": summary.get("top_champion", ""),
            "probability_sources": {k: int(v) for k, v in source_counts.items()},
        }
    )
    reports.append(manifest_path)
    try:  # refresh public website/dashboard exports; never blocks the forecast
        from src.public_export.build_public_exports import build_public_exports

        build_public_exports()
    except Exception:
        pass
    reports.extend(
        [
            write_live_state_summary(phase),
            write_finalist_prediction_summary(),
            write_live_update_limitations(fallback_usage, sim_result.get("source_counts", {})),
            gate["report"],
            validation["report"],
        ]
    )
    return {
        "status": summary["status"],
        "current_phase": phase,
        "finalist_prediction_active": summary["finalist_prediction_active"],
        "top_finalist_pair": summary.get("top_finalist_pair", ""),
        "top_finalist_pair_probability": summary.get("top_finalist_pair_probability", 0.0),
        "top_champion": summary.get("top_champion", ""),
        "top_champion_probability": summary.get("top_champion_probability", 0.0),
        "fallback_bracket_usage": fallback_usage,
        "forecast_mode": gate["forecast_mode"],
        "public_label": gate["public_label"],
        "source_quality_score": gate["source_quality_score"],
        "forecast_ran": True,
        "live_matchup_prediction_status": matchup_prediction.get("status", "unknown"),
        "live_matchups_predicted": matchup_prediction.get("predicted_rows", 0),
        "live_model_probability_uses": live_model_uses,
        "probability_source_counts": {k: int(v) for k, v in source_counts.items()},
        "run_id": run_id,
        "phase_transition": transition,
        "reports": reports,
    }
