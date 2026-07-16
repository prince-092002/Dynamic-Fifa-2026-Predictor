"""Canonical champion probabilities when the championship final is resolved."""

from __future__ import annotations

import pandas as pd

from src.live_state.live_config import coerce_bool_series, normalize_stage_name
from src.simulation.tournament_structure import is_tbd_team


FINAL_PROBABILITY_BASIS = "direct_final_matchup_probability"


def canonical_final_champion_probabilities(
    bracket: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Return direct title probabilities for one known, unresolved Final.

    The final matchup prediction is already a two-way advancement probability
    (regulation win plus half the draw mass). Sampling that same Bernoulli event
    again only adds Monte Carlo noise, so the direct values are authoritative at
    this stage. No team names or tournament-specific pairings are hardcoded.
    """
    columns = [
        "team",
        "champion_probability",
        "probability_basis",
        "source_match_id",
        "model_name",
        "probability_source",
        "prediction_generated_at",
    ]
    if bracket is None or bracket.empty or predictions is None or predictions.empty:
        return pd.DataFrame(columns=columns)

    stages = bracket.get("stage", pd.Series("", index=bracket.index)).map(normalize_stage_name)
    completed = coerce_bool_series(bracket.get("is_completed", pd.Series(False, index=bracket.index)))
    unresolved_finals = bracket[stages.eq("Final") & ~completed]
    if len(unresolved_finals) != 1:
        return pd.DataFrame(columns=columns)

    final = unresolved_finals.iloc[0]
    team_a, team_b = final.get("team_a"), final.get("team_b")
    if is_tbd_team(team_a) or is_tbd_team(team_b):
        return pd.DataFrame(columns=columns)

    candidates = predictions.copy()
    if "prediction_status" in candidates:
        candidates = candidates[candidates["prediction_status"].astype(str).str.lower().eq("predicted")]
    if "stage" in candidates:
        candidates = candidates[candidates["stage"].map(normalize_stage_name).eq("Final")]
    pair = frozenset([str(team_a), str(team_b)])
    candidates = candidates[
        candidates.apply(
            lambda row: frozenset([str(row.get("team_a")), str(row.get("team_b"))]) == pair,
            axis=1,
        )
    ]
    if len(candidates) != 1:
        return pd.DataFrame(columns=columns)

    prediction = candidates.iloc[0]
    pred_a = str(prediction.get("team_a"))
    prob_a = pd.to_numeric(prediction.get("prob_team_a_advance"), errors="coerce")
    prob_b = pd.to_numeric(prediction.get("prob_team_b_advance"), errors="coerce")
    if pd.isna(prob_a) or pd.isna(prob_b) or prob_a < 0 or prob_b < 0 or prob_a + prob_b <= 0:
        return pd.DataFrame(columns=columns)
    prob_a = float(prob_a) / float(prob_a + prob_b)
    prob_b = 1.0 - prob_a

    probability_by_team = {
        pred_a: prob_a,
        str(prediction.get("team_b")): prob_b,
    }
    shared = {
        "probability_basis": FINAL_PROBABILITY_BASIS,
        "source_match_id": prediction.get("match_id", final.get("match_id", final.get("fixture_id"))),
        "model_name": prediction.get("model_name"),
        "probability_source": prediction.get("probability_source"),
        "prediction_generated_at": prediction.get("generated_at"),
    }
    rows = [
        {"team": str(team), "champion_probability": probability_by_team[str(team)], **shared}
        for team in [team_a, team_b]
    ]
    return pd.DataFrame(rows, columns=columns).sort_values("champion_probability", ascending=False, ignore_index=True)
