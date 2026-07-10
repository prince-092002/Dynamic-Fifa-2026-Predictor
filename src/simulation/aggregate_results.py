"""Aggregate simulation outputs."""

from __future__ import annotations

import pandas as pd

from src.simulation.simulation_config import SIMULATION_OUTPUT_DIR, STAGE_SCORE, ensure_simulation_directories

STAGE_ORDER = ["Group Stage", "Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Champion"]
STAGE_INDEX = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}


def aggregate_simulation_results(simulation_result: dict) -> dict:
    ensure_simulation_directories()
    simulations = simulation_result["simulations"]
    n = simulation_result["n_simulations"]
    team_rows = [row for sim in simulations for row in sim["team_stage_results"]]
    match_rows = [row | {"simulation_id": sim["simulation_id"]} for sim in simulations[: min(100, len(simulations))] for row in sim["match_results"]]
    team_df = pd.DataFrame(team_rows)
    full_completed = sum(1 for sim in simulations if sim.get("full_bracket_completed"))
    source_counts: dict[str, int] = {"model_exact": 0, "model_reversed": 0, "elo_fallback": 0, "neutral_fallback": 0}
    for sim in simulations:
        for key, value in sim.get("probability_source_counts", {}).items():
            source_counts[key] = source_counts.get(key, 0) + int(value)
    if team_df.empty:
        advancement = pd.DataFrame(columns=["team", "simulations", "reach_group_stage_prob", "reach_round_of_32_prob", "champion_prob"])
    else:
        teams = sorted(team_df["team"].unique())
        records = []
        for team in teams:
            subset = team_df[team_df["team"] == team]
            stage_values = subset["deepest_stage"].map(STAGE_INDEX).fillna(0)
            round32 = int((stage_values >= STAGE_INDEX["Round of 32"]).sum())
            round16 = int((stage_values >= STAGE_INDEX["Round of 16"]).sum())
            qf = int((stage_values >= STAGE_INDEX["Quarterfinal"]).sum())
            sf = int((stage_values >= STAGE_INDEX["Semifinal"]).sum())
            final = int((stage_values >= STAGE_INDEX["Final"]).sum())
            champion_count = int((subset["champion"] == True).sum()) if "champion" in subset.columns else 0
            records.append(
                {
                    "team": team,
                    "simulations": n,
                    "reach_group_stage_prob": 1.0,
                    "reach_round_of_32_prob": round32 / n,
                    "reach_round_of_16_prob": round16 / n,
                    "reach_quarterfinal_prob": qf / n,
                    "reach_semifinal_prob": sf / n,
                    "reach_final_prob": final / n,
                    "champion_prob": champion_count / n if full_completed else pd.NA,
                    "avg_deepest_stage": float(stage_values.mean()),
                    "champion_count": champion_count,
                    "unresolved_note": "" if full_completed else "Full bracket did not complete in all simulations.",
                }
            )
        advancement = pd.DataFrame(records)
    advancement_path = SIMULATION_OUTPUT_DIR / "team_advancement_probabilities.csv"
    advancement.to_csv(advancement_path, index=False)
    champion = advancement[["team", "champion_count", "champion_prob"]].copy() if not advancement.empty else pd.DataFrame(columns=["team", "champion_count", "champion_prob"])
    champion_path = SIMULATION_OUTPUT_DIR / "champion_probabilities.csv"
    champion.to_csv(champion_path, index=False)
    stage_summary = advancement[["team", "reach_group_stage_prob", "reach_round_of_32_prob", "reach_round_of_16_prob", "reach_quarterfinal_prob", "reach_semifinal_prob", "reach_final_prob", "champion_prob"]].copy()
    stage_path = SIMULATION_OUTPUT_DIR / "stage_probability_summary.csv"
    stage_summary.to_csv(stage_path, index=False)
    match_sample = pd.DataFrame(match_rows)
    match_path = SIMULATION_OUTPUT_DIR / "simulated_match_results_sample.csv"
    match_sample.to_csv(match_path, index=False)
    completion = pd.DataFrame(
        [
            {
                "simulations": n,
                "full_bracket_completed_count": full_completed,
                "full_bracket_completed_rate": full_completed / n,
                "avg_unresolved_matches": sum(sim.get("unresolved_count", 0) for sim in simulations) / n,
                "model_exact_probability_uses": source_counts.get("model_exact", 0),
                "model_reversed_probability_uses": source_counts.get("model_reversed", 0),
                "elo_fallback_probability_uses": source_counts.get("elo_fallback", 0),
                "neutral_fallback_probability_uses": source_counts.get("neutral_fallback", 0),
            }
        ]
    )
    completion_path = SIMULATION_OUTPUT_DIR / "bracket_completion_summary.csv"
    completion.to_csv(completion_path, index=False)
    source_df = pd.DataFrame([{"probability_source": key, "uses": value} for key, value in source_counts.items()])
    source_path = SIMULATION_OUTPUT_DIR / "probability_source_summary.csv"
    source_df.to_csv(source_path, index=False)
    return {
        "team_advancement_path": str(advancement_path),
        "champion_probabilities_path": str(champion_path),
        "stage_probability_summary_path": str(stage_path),
        "match_sample_path": str(match_path),
        "bracket_completion_summary_path": str(completion_path),
        "probability_source_summary_path": str(source_path),
        "advancement_df": advancement,
        "champion_df": champion,
        "completion_df": completion,
        "source_df": source_df,
    }
