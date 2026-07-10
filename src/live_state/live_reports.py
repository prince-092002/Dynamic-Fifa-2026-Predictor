"""Markdown reports for live tournament-state forecasting."""

from __future__ import annotations

import json

import pandas as pd

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, coerce_bool_series, ensure_live_directories, phase_prediction_status
from src.utils.dates import now_utc_iso


def _read(path, columns=None) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns or [])


def write_live_state_summary(current_phase: str) -> str:
    ensure_live_directories()
    fixtures = _read(LIVE_STATE_DIR / "live_fixtures_normalized.csv")
    state = _read(LIVE_STATE_DIR / "current_tournament_state.csv")
    completed = int(coerce_bool_series(fixtures.get("is_completed", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
    live = int(coerce_bool_series(fixtures.get("is_live", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
    scheduled = int(coerce_bool_series(fixtures.get("is_scheduled", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
    path = LIVE_REPORT_DIR / "live_state_summary.md"
    lines = [
        "# Live State Summary",
        "",
        f"- Refresh timestamp: {now_utc_iso()}",
        f"- Current tournament phase: {current_phase}",
        f"- Completed matches: {completed}",
        f"- Live matches: {live}",
        f"- Scheduled matches: {scheduled}",
        f"- Teams tracked: {len(state)}",
        f"- Teams still alive: {int(coerce_bool_series(state.get('still_alive', pd.Series(dtype=bool))).sum()) if not state.empty else 0}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_finalist_prediction_summary() -> str:
    ensure_live_directories()
    pair = _read(LIVE_STATE_DIR / "finalist_pair_probabilities.csv")
    reach = _read(LIVE_STATE_DIR / "team_reach_final_probabilities.csv")
    champion = _read(LIVE_STATE_DIR / "live_champion_probabilities.csv")
    summary_path = LIVE_STATE_DIR / "live_forecast_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    counts_path = LIVE_STATE_DIR / "live_probability_source_counts.json"
    source_counts = json.loads(counts_path.read_text(encoding="utf-8")) if counts_path.exists() else {}
    total_sourced = sum(source_counts.values())
    live_model_uses = source_counts.get("live_model_exact", 0) + source_counts.get("live_model_reversed", 0)
    elo_uses = source_counts.get("elo_fallback", 0)
    gate_path = LIVE_STATE_DIR / "live_forecast_quality_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else {}
    provider = "football_data_org" if gate.get("football_data_org_fixture_rows", 0) > 0 else gate.get("provider", "unknown")
    phase = summary.get("current_phase", "unknown")
    path = LIVE_REPORT_DIR / "finalist_prediction_summary.md"
    lines = [
        "# Finalist Prediction Summary",
        "",
        f"- Current phase: {phase}",
        f"- Selected live provider: {provider}",
        f"- Forecast mode: {summary.get('forecast_mode', 'unknown')}",
        f"- Public label: {summary.get('public_label', 'unknown')}",
        f"- Source quality score: {summary.get('source_quality_score', 'unknown')}",
        f"- Forecast ran: {summary.get('forecast_ran', True)}",
        f"- Prediction relevance: {phase_prediction_status(phase)}",
        f"- Live model probability usage: {live_model_uses} of {total_sourced} simulated matches ({live_model_uses / total_sourced:.2%})" if total_sourced else "- Live model probability usage: not recorded",
        f"- Elo fallback probability usage: {elo_uses} of {total_sourced} simulated matches ({elo_uses / total_sourced:.2%})" if total_sourced else "- Elo fallback probability usage: not recorded",
        "",
        "## Top Finalist Pairs",
        "",
        "| Pair | Probability |",
        "|---|---:|",
    ]
    for _, row in pair.head(10).iterrows():
        lines.append(f"| {row['finalist_pair_key']} | {row['probability']:.4f} |")
    lines.extend(["", "## Top Reach-Final Teams", "", "| Team | Probability |", "|---|---:|"])
    for _, row in reach.head(10).iterrows():
        lines.append(f"| {row['team']} | {row['reach_final_probability']:.4f} |")
    lines.extend(["", "## Top Champion Probabilities", "", "| Team | Probability |", "|---|---:|"])
    for _, row in champion.head(10).iterrows():
        lines.append(f"| {row['team']} | {row['champion_probability']:.4f} |")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_live_update_limitations(fallback_bracket_usage: float = 0.0, source_counts: dict | None = None) -> str:
    ensure_live_directories()
    source_counts = source_counts or {}
    path = LIVE_REPORT_DIR / "live_update_limitations.md"
    lines = [
        "# Live Update Limitations",
        "",
        "- Predictions are probabilistic estimates, not guarantees.",
        "- API-Football availability depends on credentials, plan limits, and whether FIFA 2026 data is exposed yet.",
        "- FIFA official pages are not aggressively scraped or bypassed.",
        f"- Fallback bracket usage: {fallback_bracket_usage:.2%}",
        f"- Elo fallback probability uses: {source_counts.get('elo_fallback', 0)}",
        f"- Neutral fallback probability uses: {source_counts.get('neutral_fallback', 0)}",
        "- Missing team/player stats may limit matchup-specific feature generation.",
        "- Fallback bracket mapping is not official FIFA mapping.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_end_of_matchday_update_summary(update_result: dict, live_result: dict | None = None) -> str:
    ensure_live_directories()
    live_result = live_result or {}
    path = LIVE_REPORT_DIR / "end_of_matchday_update_summary.md"
    lines = [
        "# End-of-Matchday Update Summary",
        "",
        f"- Refresh timestamp: {now_utc_iso()}",
        f"- Update status: {update_result.get('validation_status', update_result.get('status', 'unknown'))}",
        f"- New completed matches detected: {update_result.get('new_completed_matches_detected', 0)}",
        f"- Live forecast status: {live_result.get('status', 'not_run')}",
        f"- Forecast ran: {live_result.get('forecast_ran', False)}",
        f"- Forecast mode: {live_result.get('forecast_mode', 'unknown')}",
        f"- Public label: {live_result.get('public_label', 'unknown')}",
        f"- Source quality score: {live_result.get('source_quality_score', 'unknown')}",
        f"- Current phase: {live_result.get('current_phase', 'unknown')}",
        f"- Fallback usage: {live_result.get('fallback_bracket_usage', 0):.2%}" if isinstance(live_result.get("fallback_bracket_usage", 0), (int, float)) else f"- Fallback usage: {live_result.get('fallback_bracket_usage', 'unknown')}",
        f"- Live matchup predictions: {live_result.get('live_matchup_prediction_status', 'not_run')} ({live_result.get('live_matchups_predicted', 0)} matchups predicted by the model)",
        f"- Live model probability uses in simulation: {live_result.get('live_model_probability_uses', 0)}",
        f"- Tournament phase before update: {(live_result.get('phase_transition') or {}).get('previous_phase', 'unknown')}",
        f"- Tournament phase after update: {(live_result.get('phase_transition') or {}).get('current_phase', live_result.get('current_phase', 'unknown'))}",
        f"- Phase transition detected: {(live_result.get('phase_transition') or {}).get('phase_changed', False)}",
        f"- Newly completed matches (since last forecast run): {(live_result.get('phase_transition') or {}).get('newly_completed_matches', 0)}",
        f"- Newly resolved knockout matchups: {(live_result.get('phase_transition') or {}).get('newly_resolved_matchups', 0)}",
        f"- New XGBoost predictions generated: {live_result.get('live_matchups_predicted', 0)}",
        f"- Why or why not: {live_result.get('reason', 'forecast ran or no blocking reason reported')}",
        f"- Top finalist pair: {live_result.get('top_finalist_pair', '')}",
        f"- Top champion: {live_result.get('top_champion', '')}",
        f"- Next recommended action: {live_result.get('next_recommended_action', 'Use --allow-fallback-forecast only for testing when the gate reports fallback_pre_tournament_forecast.')}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
