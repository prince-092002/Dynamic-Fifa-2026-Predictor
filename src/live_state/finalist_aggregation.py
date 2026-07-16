"""Aggregate live finalist simulation outputs."""

from __future__ import annotations

import json

import pandas as pd

from src.live_state.final_stage_probability import canonical_final_champion_probabilities
from src.live_state.live_config import LIVE_STATE_DIR, ensure_live_directories


def aggregate_live_finalist_results(
    simulation_df: pd.DataFrame | None = None,
    bracket_df: pd.DataFrame | None = None,
    predictions_df: pd.DataFrame | None = None,
) -> dict:
    ensure_live_directories()
    simulations = simulation_df if simulation_df is not None else pd.read_csv(LIVE_STATE_DIR / "live_finalist_simulation_results.csv")
    n = len(simulations)
    pair = simulations.groupby("finalist_pair_key", dropna=False).size().reset_index(name="count") if n else pd.DataFrame(columns=["finalist_pair_key", "count"])
    if not pair.empty:
        pair["probability"] = pair["count"] / n
        pair[["finalist_team_1", "finalist_team_2"]] = pair["finalist_pair_key"].str.split(" vs ", n=1, expand=True)
        pair = pair[["finalist_team_1", "finalist_team_2", "finalist_pair_key", "count", "probability"]].sort_values("probability", ascending=False)
    reach_rows = []
    for column in ["finalist_1", "finalist_2"]:
        reach_rows.extend(simulations[column].dropna().astype(str).tolist() if column in simulations else [])
    reach = pd.Series(reach_rows).value_counts().rename_axis("team").reset_index(name="reach_final_count") if reach_rows else pd.DataFrame(columns=["team", "reach_final_count"])
    if not reach.empty:
        reach["reach_final_probability"] = reach["reach_final_count"] / n
    champion = simulations["champion"].dropna().astype(str).value_counts().rename_axis("team").reset_index(name="champion_count") if n and "champion" in simulations else pd.DataFrame(columns=["team", "champion_count"])
    if not champion.empty:
        champion["monte_carlo_champion_probability"] = champion["champion_count"] / n
        champion["champion_probability"] = champion["monte_carlo_champion_probability"]
        champion["probability_basis"] = "monte_carlo_simulation"

    bracket = bracket_df if bracket_df is not None else _read_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
    predictions = predictions_df if predictions_df is not None else _read_csv(LIVE_STATE_DIR / "live_knockout_match_predictions.csv")
    canonical = canonical_final_champion_probabilities(bracket, predictions)
    if not canonical.empty:
        diagnostics = champion[["team", "champion_count", "monte_carlo_champion_probability"]].copy()
        champion = canonical.merge(diagnostics, on="team", how="left")
        champion = champion[
            [
                "team",
                "champion_count",
                "monte_carlo_champion_probability",
                "champion_probability",
                "probability_basis",
                "source_match_id",
                "model_name",
                "probability_source",
                "prediction_generated_at",
            ]
        ]
    elif not champion.empty:
        champion = champion.sort_values("champion_probability", ascending=False, ignore_index=True)
    summary = {
        "simulations": n,
        "top_finalist_pair": pair.iloc[0]["finalist_pair_key"] if not pair.empty else "",
        "top_finalist_pair_probability": float(pair.iloc[0]["probability"]) if not pair.empty else 0.0,
        "top_champion": champion.iloc[0]["team"] if not champion.empty else "",
        "top_champion_probability": float(champion.iloc[0]["champion_probability"]) if not champion.empty else 0.0,
        "champion_probability_basis": champion.iloc[0]["probability_basis"] if not champion.empty else "unavailable",
        "monte_carlo_top_champion": champion.sort_values("monte_carlo_champion_probability", ascending=False).iloc[0]["team"] if not champion.empty else "",
        "monte_carlo_top_champion_probability": float(champion["monte_carlo_champion_probability"].max()) if not champion.empty else 0.0,
        "fallback_mapping_used": bool(simulations.get("fallback_mapping_used", pd.Series(dtype=bool)).any()) if n else False,
    }
    pair_path = LIVE_STATE_DIR / "finalist_pair_probabilities.csv"
    reach_path = LIVE_STATE_DIR / "team_reach_final_probabilities.csv"
    champion_path = LIVE_STATE_DIR / "live_champion_probabilities.csv"
    summary_path = LIVE_STATE_DIR / "live_forecast_summary.json"
    pair.to_csv(pair_path, index=False)
    reach.to_csv(reach_path, index=False)
    champion.to_csv(champion_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"pair": pair, "reach": reach, "champion": champion, "summary": summary, "paths": [str(pair_path), str(reach_path), str(champion_path), str(summary_path)]}


def _read_csv(path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
