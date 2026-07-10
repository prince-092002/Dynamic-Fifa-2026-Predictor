"""Integration check: a newly resolved knockout matchup flows to live model predictions.

Simulates the moment the real quarterfinals finish and the semifinal pairings become
known, entirely inside a sandbox directory. Production files in outputs/live_state are
read-only inputs and are never modified.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd

from src.live_state import live_matchup_features, live_matchup_predictor
from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, ensure_live_directories
from src.live_state.finalist_simulator import _simulate_or_lock_knockout_match
from src.simulation.bracket_mapping import get_dynamic_match_probabilities
from src.utils.dates import now_utc_iso

FLOW_REPORT_PATH = LIVE_REPORT_DIR / "live_matchup_flow_integration_report.md"


def _build_synthetic_state(sandbox: Path) -> dict:
    """Copy real live state into the sandbox, then complete the QFs and resolve the semis."""
    bracket = pd.read_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
    fixtures = pd.read_csv(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
    for frame in (bracket, fixtures):
        for column, target in [("winner", "object"), ("team_a", "object"), ("team_b", "object"), ("status", "object")]:
            if column in frame.columns:
                frame[column] = frame[column].astype(target)
    synthetic_qf_winners = {}
    qf_mask = bracket["stage"].astype(str).eq("Quarterfinal")
    for idx in bracket[qf_mask].index:
        winner = bracket.at[idx, "team_a"]  # deterministic synthetic outcome: team_a advances
        synthetic_qf_winners[str(bracket.at[idx, "fixture_id"])] = winner
        bracket.at[idx, "winner"] = winner
        bracket.at[idx, "status"] = "FINISHED"
        bracket.at[idx, "is_completed"] = True
        bracket.at[idx, "is_scheduled"] = False
    qf_winners = list(synthetic_qf_winners.values())
    semi_mask = bracket["stage"].astype(str).eq("Semifinal")
    semi_indices = list(bracket[semi_mask].index)
    resolved_semis = []
    for slot, idx in enumerate(semi_indices[:2]):
        team_a, team_b = qf_winners[2 * slot], qf_winners[2 * slot + 1]
        bracket.at[idx, "team_a"] = team_a
        bracket.at[idx, "team_b"] = team_b
        bracket.at[idx, "is_tbd"] = False
        resolved_semis.append((team_a, team_b))
    for idx, row in fixtures.iterrows():
        fixture_id = str(row.get("fixture_id"))
        if fixture_id in synthetic_qf_winners:
            fixtures.at[idx, "status_short"] = "FINISHED"
            fixtures.at[idx, "status_long"] = "FINISHED"
            fixtures.at[idx, "is_completed"] = True
            fixtures.at[idx, "is_scheduled"] = False
            fixtures.at[idx, "team_a_goals"] = 1.0
            fixtures.at[idx, "team_b_goals"] = 0.0
            fixtures.at[idx, "winner"] = synthetic_qf_winners[fixture_id]
    semi_fixture_rows = fixtures[fixtures["stage"].astype(str).eq("Semifinal")].index
    for slot, idx in enumerate(list(semi_fixture_rows)[:2]):
        fixtures.at[idx, "team_a"] = resolved_semis[slot][0]
        fixtures.at[idx, "team_b"] = resolved_semis[slot][1]
    bracket.to_csv(sandbox / "merged_bracket_state.csv", index=False)
    fixtures.to_csv(sandbox / "football_data_org_fixtures_normalized.csv", index=False)
    return {"resolved_semis": resolved_semis, "completed_qf_bracket": bracket[qf_mask]}


def run_live_matchup_flow_check() -> dict:
    """End-to-end check: identify -> features -> predict -> lookup -> simulator source."""
    ensure_live_directories()
    sandbox = Path(tempfile.mkdtemp(prefix="live_flow_check_"))
    originals = {
        "features_state_dir": live_matchup_features.LIVE_STATE_DIR,
        "matchups_path": live_matchup_features.REMAINING_MATCHUPS_PATH,
        "features_path": live_matchup_features.LIVE_FEATURES_PATH,
        "predictor_features_path": live_matchup_predictor.LIVE_FEATURES_PATH,
        "predictions_path": live_matchup_predictor.LIVE_PREDICTIONS_PATH,
    }
    checks = []
    try:
        synthetic = _build_synthetic_state(sandbox)
        live_matchup_features.LIVE_STATE_DIR = sandbox
        live_matchup_features.REMAINING_MATCHUPS_PATH = sandbox / "remaining_known_knockout_matchups.csv"
        live_matchup_features.LIVE_FEATURES_PATH = sandbox / "live_knockout_match_features.csv"
        live_matchup_predictor.LIVE_FEATURES_PATH = sandbox / "live_knockout_match_features.csv"
        live_matchup_predictor.LIVE_PREDICTIONS_PATH = sandbox / "live_knockout_match_predictions.csv"

        matchups = live_matchup_features.identify_remaining_live_knockout_matches()
        semi_matchups = matchups[matchups["stage"].astype(str).eq("Semifinal")]
        checks.append(("newly_resolved_matchups_detected", len(semi_matchups) == 2, f"{len(semi_matchups)} of 2 synthetic semifinals detected; {len(matchups)} matchups total"))
        completed_in_matchups = 0
        if not matchups.empty:
            completed_ids = set(synthetic["completed_qf_bracket"]["match_id"].astype(str))
            completed_in_matchups = int(matchups["match_id"].astype(str).isin(completed_ids).sum())
        checks.append(("completed_matches_excluded", completed_in_matchups == 0, f"{completed_in_matchups} completed QFs leaked into matchups"))

        features = live_matchup_features.build_live_knockout_features()
        semi_features = features[features["stage"].astype(str).eq("Semifinal")] if not features.empty else pd.DataFrame()
        checks.append(("features_built_for_new_matchups", len(semi_features) == 2 and bool(semi_features["is_predictable_now"].all()), f"{len(semi_features)} semifinal feature rows, predictable: {semi_features['is_predictable_now'].tolist() if not semi_features.empty else []}"))

        prediction_result = live_matchup_predictor.predict_live_knockout_matchups()
        predictions = pd.read_csv(live_matchup_predictor.LIVE_PREDICTIONS_PATH)
        semi_predictions = predictions[(predictions["stage"].astype(str).eq("Semifinal")) & (predictions["prediction_status"] == "predicted")]
        checks.append(("model_predictions_generated", len(semi_predictions) == 2, f"{len(semi_predictions)} of 2 semifinals predicted by {prediction_result['model_name']}"))

        lookup = live_matchup_predictor.load_live_knockout_prediction_lookup()
        team_a, team_b = synthetic["resolved_semis"][0]
        _, exact_source = get_dynamic_match_probabilities(team_a, team_b, {}, {}, live_probability_lookup=lookup)
        _, reversed_source = get_dynamic_match_probabilities(team_b, team_a, {}, {}, live_probability_lookup=lookup)
        checks.append(("simulator_uses_live_model_exact", exact_source == "live_model_exact", f"source for {team_a} vs {team_b}: {exact_source}"))
        checks.append(("simulator_uses_live_model_reversed", reversed_source == "live_model_reversed", f"source for {team_b} vs {team_a}: {reversed_source}"))
        _, unknown_source = get_dynamic_match_probabilities("Argentina", "France", {}, {"Argentina": 1900.0, "France": 1880.0}, live_probability_lookup=lookup)
        checks.append(("elo_only_without_prediction", unknown_source == "elo_fallback", f"source for pair without live prediction: {unknown_source}"))

        import numpy as np

        rng = np.random.default_rng(42)
        completed_row = synthetic["completed_qf_bracket"].iloc[0].to_dict()
        winner, _, label, source = _simulate_or_lock_knockout_match(completed_row, rng, {}, {}, lookup)
        checks.append(("completed_results_locked_in_simulator", source == "completed_result" and str(winner) == str(completed_row["winner"]), f"completed QF returned winner={winner}, source={source}"))
    finally:
        live_matchup_features.LIVE_STATE_DIR = originals["features_state_dir"]
        live_matchup_features.REMAINING_MATCHUPS_PATH = originals["matchups_path"]
        live_matchup_features.LIVE_FEATURES_PATH = originals["features_path"]
        live_matchup_predictor.LIVE_FEATURES_PATH = originals["predictor_features_path"]
        live_matchup_predictor.LIVE_PREDICTIONS_PATH = originals["predictions_path"]
        shutil.rmtree(sandbox, ignore_errors=True)

    status = "pass" if all(ok for _, ok, _ in checks) else "fail"
    lines = [
        "# Live Matchup Flow Integration Check",
        "",
        f"- Generated: {now_utc_iso()}",
        f"- Status: {status}",
        "",
        "Synthetic scenario: all four real quarterfinals are marked completed (team_a advances)",
        "and the two semifinal pairings become known. Run in an isolated sandbox; production",
        "live-state files are never modified.",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in checks:
        lines.append(f"| {name} | {'pass' if ok else 'fail'} | {detail} |")
    FLOW_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return {"status": status, "checks": checks, "report": str(FLOW_REPORT_PATH)}
