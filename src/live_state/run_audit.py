"""Run auditability: phase transitions, probability-source history, run manifests."""

from __future__ import annotations

import json
import uuid

import pandas as pd

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, ensure_live_directories
from src.utils.dates import now_utc_iso

PHASE_TRANSITION_PATH = LIVE_STATE_DIR / "tournament_phase_transition.json"
SOURCE_HISTORY_PATH = LIVE_STATE_DIR / "probability_source_history.csv"
PROGRESSION_REPORT_PATH = LIVE_REPORT_DIR / "probability_source_progression.md"
MANIFEST_PATH = LIVE_STATE_DIR / "latest_live_run_manifest.json"

SOURCE_COLUMNS = ["live_model_exact", "live_model_reversed", "model_exact", "model_reversed", "elo_fallback", "neutral_fallback"]


def _read_json(path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def new_run_id() -> str:
    return f"{now_utc_iso().replace(':', '').replace('+0000', 'Z')}-{uuid.uuid4().hex[:8]}"


def record_phase_transition(current_phase: str, completed_match_count: int, resolved_matchup_ids: list[str]) -> dict:
    """Compare tournament phase and state against the previous recorded run.

    All counts are derived from actual state: completed matches from the quality
    gate, resolved matchups from remaining_known_knockout_matchups.csv.
    """
    ensure_live_directories()
    previous = _read_json(PHASE_TRANSITION_PATH)
    previous_phase = previous.get("current_phase")
    previous_completed = previous.get("completed_match_count")
    previous_ids = set(previous.get("resolved_matchup_ids", []))
    newly_resolved = [m for m in resolved_matchup_ids if m not in previous_ids] if previous else []
    payload = {
        "previous_phase": previous_phase,
        "current_phase": current_phase,
        "phase_changed": bool(previous_phase) and previous_phase != current_phase,
        "detected_at": now_utc_iso(),
        "newly_resolved_matchups": len(newly_resolved),
        "newly_completed_matches": max(int(completed_match_count) - int(previous_completed), 0) if isinstance(previous_completed, int) else 0,
        "completed_match_count": int(completed_match_count),
        "resolved_matchup_ids": [str(m) for m in resolved_matchup_ids],
        "first_recorded_run": not bool(previous),
    }
    PHASE_TRANSITION_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def append_probability_source_history(run_id: str, phase: str, simulations: int, known_matchups: int, live_predictions: int, source_counts: dict) -> pd.DataFrame:
    """Append one row per forecast run so model coverage is observable over time."""
    ensure_live_directories()
    total = int(sum(source_counts.values()))
    model_driven = sum(int(source_counts.get(k, 0)) for k in ["live_model_exact", "live_model_reversed", "model_exact", "model_reversed"])
    fallback = sum(int(source_counts.get(k, 0)) for k in ["elo_fallback", "neutral_fallback"])
    row = {
        "run_id": run_id,
        "timestamp": now_utc_iso(),
        "tournament_phase": phase,
        "simulation_count": int(simulations),
        "known_remaining_matchups": int(known_matchups),
        "live_model_predictions_available": int(live_predictions),
        **{k: int(source_counts.get(k, 0)) for k in SOURCE_COLUMNS},
        "total_simulated_decisions": total,
        "model_driven_pct": round(model_driven / total, 6) if total else 0.0,
        "fallback_pct": round(fallback / total, 6) if total else 0.0,
    }
    history = pd.read_csv(SOURCE_HISTORY_PATH) if SOURCE_HISTORY_PATH.exists() else pd.DataFrame()
    if not history.empty and "run_id" in history.columns:
        history = history[history["run_id"].astype(str) != run_id]
    history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
    history.to_csv(SOURCE_HISTORY_PATH, index=False)
    return history


def append_forecast_history(run_id: str, phase: str, simulations: int, provider: str, forecast_mode: str) -> dict:
    """Append per-team and per-pair forecast snapshots for this run.

    Append-safe and deduplicated by run_id; historical rows are never rewritten
    and no backfill is invented. Written by the forecasting pipeline only.
    """
    ensure_live_directories()
    timestamp = now_utc_iso()
    common = {"run_id": run_id, "timestamp": timestamp, "phase": phase, "simulation_count": int(simulations), "provider": provider, "forecast_mode": forecast_mode}
    specs = [
        ("live_champion_probabilities.csv", "champion_probability_history.csv", ["team"], "champion_probability"),
        ("team_reach_final_probabilities.csv", "finalist_probability_history.csv", ["team"], "reach_final_probability"),
        ("finalist_pair_probabilities.csv", "finalist_pair_probability_history.csv", ["finalist_team_1", "finalist_team_2"], "probability"),
    ]
    written = {}
    for source_name, history_name, id_columns, value_column in specs:
        source_path = LIVE_STATE_DIR / source_name
        if not source_path.exists():
            continue
        source = pd.read_csv(source_path)
        if source.empty or value_column not in source.columns:
            continue
        rows = []
        for _, row in source.iterrows():
            rows.append({**common, **{c: row[c] for c in id_columns if c in source.columns}, value_column: float(row[value_column])})
        history_path = LIVE_STATE_DIR / history_name
        history = pd.read_csv(history_path) if history_path.exists() else pd.DataFrame()
        if not history.empty and "run_id" in history.columns:
            history = history[history["run_id"].astype(str) != run_id]
        history = pd.concat([history, pd.DataFrame(rows)], ignore_index=True)
        history.to_csv(history_path, index=False)
        written[history_name] = len(rows)
    return written


def write_probability_source_progression_report() -> str:
    ensure_live_directories()
    history = pd.read_csv(SOURCE_HISTORY_PATH) if SOURCE_HISTORY_PATH.exists() else pd.DataFrame()
    lines = ["# Probability Source Progression", "", f"- Generated: {now_utc_iso()}", ""]
    if history.empty:
        lines.append("No forecast runs recorded yet.")
    else:
        lines.extend(
            [
                "Model coverage per live forecast run. The fallback share is expected to shrink",
                "as real knockout rounds resolve and more matchups receive live model predictions.",
                "",
                "| Timestamp | Phase | Simulations | Known matchups | Live predictions | Model-driven | Fallback |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for _, row in history.iterrows():
            lines.append(
                f"| {row['timestamp']} | {row['tournament_phase']} | {row['simulation_count']} | {row['known_remaining_matchups']} "
                f"| {row['live_model_predictions_available']} | {row['model_driven_pct']:.2%} | {row['fallback_pct']:.2%} |"
            )
        if len(history) >= 2:
            prev, curr = history.iloc[-2], history.iloc[-1]
            lines.extend(
                [
                    "",
                    "## Previous vs Current Run",
                    "",
                    f"- Phase: {prev['tournament_phase']} -> {curr['tournament_phase']}",
                    f"- Model-driven share: {prev['model_driven_pct']:.2%} -> {curr['model_driven_pct']:.2%}",
                    f"- Fallback share: {prev['fallback_pct']:.2%} -> {curr['fallback_pct']:.2%}",
                    f"- Live model predictions available: {int(prev['live_model_predictions_available'])} -> {int(curr['live_model_predictions_available'])}",
                ]
            )
        lines.extend(
            [
                "",
                "## Reference Baseline",
                "",
                "- Phase 5E (pre live-matchup predictions), quarterfinal stage: fallback share was 99.63%.",
                "- Values above are actual observed results per run; nothing is projected or hardcoded.",
            ]
        )
    PROGRESSION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(PROGRESSION_REPORT_PATH)


def write_run_manifest(fields: dict) -> str:
    """Persist a manifest describing exactly what the latest forecast run did."""
    ensure_live_directories()
    freshness = _read_json(LIVE_STATE_DIR / "live_provider_freshness.json")
    validation_report = LIVE_STATE_DIR.parent / "reports" / "data_validation_report.csv"
    broader = "not_available"
    if validation_report.exists():
        try:
            report = pd.read_csv(validation_report)
            broader = "fail" if report["status"].eq("fail").any() else "pass"
        except Exception:
            broader = "unreadable"
    manifest = {
        **fields,
        "data_source_mode": freshness.get("data_source_mode", "unknown"),
        "provider_data_age_minutes": freshness.get("data_age_minutes"),
        "provider_rate_limited": freshness.get("rate_limited"),
        "broader_refresh_validation": broader,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(MANIFEST_PATH)
