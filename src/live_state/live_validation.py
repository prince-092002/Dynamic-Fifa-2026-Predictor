"""Validation checks for live finalist forecasts."""

from __future__ import annotations

import json

import pandas as pd

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, coerce_bool_series, ensure_live_directories, phase_prediction_status


def _row(check: str, status: str, message: str, rows_affected: int = 0) -> dict:
    return {"check": check, "status": status, "message": message, "rows_affected": rows_affected}


VALID_PROBABILITY_SOURCES = {
    "completed_result",
    "live_model_exact",
    "live_model_reversed",
    "model_prediction_file",
    "model_exact",
    "model_reversed",
    "elo_fallback",
    "neutral_fallback",
    "unresolved_tbd",
}


def _surviving_teams_from_bracket() -> set:
    """Teams still alive in the knockout bracket.

    Survivors are teams in unplayed known matchups plus winners of completed
    knockout matches (their next-round slot may still be TBD), minus every team
    that lost a completed knockout match.
    """
    from src.simulation.tournament_structure import is_tbd_team

    bracket_path = LIVE_STATE_DIR / "merged_bracket_state.csv"
    bracket = pd.read_csv(bracket_path) if bracket_path.exists() else pd.DataFrame()
    if bracket.empty:
        return set()
    completed = coerce_bool_series(bracket.get("is_completed", pd.Series(False, index=bracket.index)))
    teams = set()
    losers = set()
    for idx, row in bracket.iterrows():
        team_a, team_b = row.get("team_a"), row.get("team_b")
        if bool(completed.loc[idx]):
            winner = row.get("winner")
            if pd.notna(winner) and not is_tbd_team(winner):
                teams.add(str(winner))
                for team in [team_a, team_b]:
                    if pd.notna(team) and str(team) != str(winner):
                        losers.add(str(team))
            continue
        if pd.notna(team_a) and pd.notna(team_b) and not is_tbd_team(team_a) and not is_tbd_team(team_b):
            teams.update([str(team_a), str(team_b)])
    return teams - losers


def _integrity_checks(probabilities: pd.DataFrame, summary: dict, gate: dict, forecast_ran: bool) -> list[dict]:
    rows = []
    champion_path = LIVE_STATE_DIR / "live_champion_probabilities.csv"
    pair_path = LIVE_STATE_DIR / "finalist_pair_probabilities.csv"
    champion = pd.read_csv(champion_path) if champion_path.exists() else pd.DataFrame()
    pair = pd.read_csv(pair_path) if pair_path.exists() else pd.DataFrame()

    # Completed results locked: fixed 1/0 probabilities, never marked simulated.
    if not probabilities.empty:
        completed = probabilities[coerce_bool_series(probabilities.get("is_completed", pd.Series(False, index=probabilities.index)))]
        simulated_completed = int(coerce_bool_series(completed.get("is_simulated", pd.Series(False, index=completed.index))).sum())
        bad_source = int((~completed.get("probability_source", pd.Series("", index=completed.index)).astype(str).eq("completed_result")).sum())
        with_probs = completed[pd.to_numeric(completed.get("prob_team_a_win"), errors="coerce").notna()]
        unlocked = int((~pd.to_numeric(with_probs["prob_team_a_win"], errors="coerce").isin([0.0, 1.0]) & ~pd.to_numeric(with_probs.get("prob_draw"), errors="coerce").eq(1.0)).sum())
        ok = simulated_completed == 0 and bad_source == 0 and unlocked == 0
        rows.append(_row("completed_results_locked", "pass" if ok else "fail", f"{len(completed)} completed rows; {simulated_completed} marked simulated, {bad_source} mislabeled sources, {unlocked} without locked probabilities", simulated_completed + bad_source + unlocked))
        # Source labels: only the known vocabulary is allowed, so fallback can never masquerade as a model.
        sources = probabilities.get("probability_source", pd.Series(dtype=str)).dropna().astype(str)
        unknown = sorted(set(sources) - VALID_PROBABILITY_SOURCES)
        rows.append(_row("probability_source_labels_valid", "pass" if not unknown else "fail", f"unknown sources: {unknown}" if unknown else "all probability_source labels are from the declared vocabulary"))
        # Live-model labels must be backed by actual prediction rows.
        live_labeled = probabilities[sources.str.startswith("live_model").reindex(probabilities.index, fill_value=False)]
        predictions_path = LIVE_STATE_DIR / "live_knockout_match_predictions.csv"
        predictions = pd.read_csv(predictions_path) if predictions_path.exists() else pd.DataFrame()
        predicted_pairs = set()
        if not predictions.empty:
            for _, p in predictions[predictions.get("prediction_status", "") == "predicted"].iterrows():
                predicted_pairs.add(frozenset([str(p["team_a"]), str(p["team_b"])]))
        unbacked = 0
        for _, row in live_labeled.iterrows():
            if frozenset([str(row.get("team_a")), str(row.get("team_b"))]) not in predicted_pairs:
                unbacked += 1
        rows.append(_row("live_model_labels_backed_by_predictions", "pass" if unbacked == 0 else "fail", f"{unbacked} rows labeled live_model_* without a matching predicted matchup", unbacked))
        # Resolved, unplayed matchups with a live prediction must actually use it.
        unplayed = probabilities[~coerce_bool_series(probabilities.get("is_completed", pd.Series(False, index=probabilities.index)))]
        missed = 0
        for _, row in unplayed.iterrows():
            pair_key = frozenset([str(row.get("team_a")), str(row.get("team_b"))])
            if pair_key in predicted_pairs and not str(row.get("probability_source", "")).startswith("live_model"):
                missed += 1
        rows.append(_row("live_model_used_when_prediction_exists", "pass" if missed == 0 else "fail", f"{missed} resolved matchups with live predictions not using them", missed))
    if forecast_ran and not champion.empty:
        surviving = _surviving_teams_from_bracket()
        if surviving:
            bad_champions = sorted(set(champion["team"].astype(str)) - surviving)
            rows.append(_row("no_eliminated_team_as_champion", "pass" if not bad_champions else "fail", f"teams outside surviving bracket: {bad_champions}" if bad_champions else f"all {len(champion)} champion candidates are in the surviving bracket ({len(surviving)} teams)"))
            finalists = set()
            for column in ["finalist_team_1", "finalist_team_2"]:
                finalists.update(pair.get(column, pd.Series(dtype=str)).dropna().astype(str))
            bad_finalists = sorted(finalists - surviving)
            rows.append(_row("no_eliminated_team_as_finalist", "pass" if not bad_finalists else "fail", f"teams outside surviving bracket: {bad_finalists}" if bad_finalists else "all finalist teams are in the surviving bracket"))
        else:
            rows.append(_row("no_eliminated_team_as_champion", "warn", "no unplayed known bracket rows to derive the surviving set from"))
        tbd_teams = [t for t in champion["team"].astype(str) if t.upper().startswith("TBD")]
        rows.append(_row("no_placeholder_teams_in_outputs", "pass" if not tbd_teams else "fail", f"placeholder teams in champion output: {tbd_teams}" if tbd_teams else "no TBD/placeholder team appears in forecast outputs"))
        prob_values = pd.to_numeric(champion.get("champion_probability", pd.Series(dtype=float)), errors="coerce")
        in_range = bool(((prob_values >= 0) & (prob_values <= 1)).all())
        rows.append(_row("probabilities_numerically_valid", "pass" if in_range else "fail", "champion probabilities within [0, 1]" if in_range else "champion probability outside [0, 1]"))
    if summary.get("forecast_mode") and gate.get("forecast_mode"):
        agrees = str(summary.get("forecast_mode")) == str(gate.get("forecast_mode"))
        rows.append(_row("forecast_mode_agrees_with_gate", "pass" if agrees else "fail", f"summary={summary.get('forecast_mode')} gate={gate.get('forecast_mode')}"))
    elif gate.get("forecast_mode"):
        rows.append(_row("forecast_mode_agrees_with_gate", "warn", "summary not enriched with forecast_mode yet (validation ran mid-pipeline); rerun validate-live-forecast after the run to cross-check"))
    freshness_path = LIVE_STATE_DIR / "live_provider_freshness.json"
    if freshness_path.exists():
        freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
        disclosed = freshness.get("data_source_mode") in {"fresh_api", "cached_normalized", "saved_snapshot", "fallback_provider", "unavailable"}
        stale_as_fresh = freshness.get("data_source_mode") == "fresh_api" and (freshness.get("cache_used") or freshness.get("snapshot_used"))
        rows.append(_row("provider_freshness_disclosed", "pass" if disclosed and not stale_as_fresh else "fail", f"data_source_mode={freshness.get('data_source_mode')}, cache_used={freshness.get('cache_used')}, snapshot_used={freshness.get('snapshot_used')}"))
    else:
        rows.append(_row("provider_freshness_disclosed", "warn", "live_provider_freshness.json not written yet"))
    return rows


def validate_live_forecast() -> dict:
    ensure_live_directories()
    rows = []
    fixtures_path = LIVE_STATE_DIR / "live_fixtures_normalized.csv"
    state_path = LIVE_STATE_DIR / "current_tournament_state.csv"
    probs_path = LIVE_STATE_DIR / "remaining_match_probabilities.csv"
    pair_path = LIVE_STATE_DIR / "finalist_pair_probabilities.csv"
    champion_path = LIVE_STATE_DIR / "live_champion_probabilities.csv"
    summary_path = LIVE_STATE_DIR / "live_forecast_summary.json"
    gate_path = LIVE_STATE_DIR / "live_forecast_quality_gate.json"
    bracket_report = LIVE_REPORT_DIR / "live_bracket_source_report.md"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    forecast_ran = bool(summary.get("forecast_ran", True))
    rows.append(_row("live_quality_gate_exists", "pass" if gate_path.exists() else "fail", str(gate_path)))
    if summary.get("forecast_mode"):
        rows.append(_row("forecast_mode_clear", "pass", f"mode={summary.get('forecast_mode')}; label={summary.get('public_label', '')}"))
    rows.append(_row("live_fixtures_file_exists", "pass" if fixtures_path.exists() else "fail", str(fixtures_path)))
    rows.append(_row("current_state_exists", "pass" if state_path.exists() else "fail", str(state_path)))
    probabilities = pd.read_csv(probs_path) if probs_path.exists() else pd.DataFrame()
    missing_probs = 0
    if not probabilities.empty:
        completed = coerce_bool_series(probabilities.get("is_completed", pd.Series(False, index=probabilities.index)))
        simulated_flag = coerce_bool_series(probabilities.get("is_simulated", pd.Series(False, index=probabilities.index)))
        remaining = probabilities[~completed]
        simulated = remaining[simulated_flag.loc[remaining.index]]
        missing_probs = int(simulated[["prob_team_a_loss", "prob_draw", "prob_team_a_win"]].isna().any(axis=1).sum()) if not simulated.empty else 0
    rows.append(_row("remaining_matches_have_probabilities", "pass" if probs_path.exists() and missing_probs == 0 else "fail", f"{missing_probs} simulated rows missing probabilities", missing_probs))
    if forecast_ran:
        pair = pd.read_csv(pair_path) if pair_path.exists() else pd.DataFrame()
        pair_sum = pd.to_numeric(pair.get("probability", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        rows.append(_row("finalist_pair_probability_sum", "pass" if abs(pair_sum - 1.0) <= 0.01 else "fail", f"sum={pair_sum:.4f}"))
        champion = pd.read_csv(champion_path) if champion_path.exists() else pd.DataFrame()
        champion_sum = pd.to_numeric(champion.get("champion_probability", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        rows.append(_row("champion_probability_sum", "pass" if abs(champion_sum - 1.0) <= 0.01 else "fail", f"sum={champion_sum:.4f}"))
    else:
        rows.append(_row("finalist_pair_probability_sum", "pass", "Forecast did not run because the quality gate blocked it."))
        rows.append(_row("champion_probability_sum", "pass", "Forecast did not run because the quality gate blocked it."))
    rows.append(_row("fallback_usage_reported", "pass" if bracket_report.exists() else "fail", str(bracket_report)))
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else {}
    phase = gate.get("current_phase")
    if not phase:
        state = pd.read_csv(state_path) if state_path.exists() else pd.DataFrame()
        phase = state["current_stage"].iloc[0] if not state.empty and "current_stage" in state else "unknown"
    relevance = phase_prediction_status(str(phase))
    rows.append(_row("current_phase_detected", "pass" if phase != "unknown" else "warn", f"phase={phase}; relevance={relevance}"))
    rows.extend(_integrity_checks(probabilities, summary, gate, forecast_ran))
    df = pd.DataFrame(rows)
    csv_path = LIVE_REPORT_DIR / "live_validation_report.csv"
    md_path = LIVE_REPORT_DIR / "live_validation_report.md"
    df.to_csv(csv_path, index=False)
    lines = ["# Live Forecast Validation Report", "", "| Check | Status | Message | Rows affected |", "|---|---|---|---:|"]
    for _, row in df.iterrows():
        lines.append(f"| {row['check']} | {row['status']} | {row['message']} | {row['rows_affected']} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "fail" if (df["status"] == "fail").any() else "pass", "report": str(md_path), "csv": str(csv_path)}
