"""Sampling helpers for match outcomes."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.simulation.tournament_structure import is_tbd_team

FALLBACK_PROBS = (0.35, 0.30, 0.35)


def normalize_probabilities(prob_loss, prob_draw, prob_win):
    values = pd.to_numeric(pd.Series([prob_loss, prob_draw, prob_win]), errors="coerce").astype(float).to_numpy()
    if np.isnan(values).any():
        return None
    values = np.clip(values, 0, None)
    total = values.sum()
    if total <= 0:
        return FALLBACK_PROBS
    return tuple(values / total)


def fallback_match_probabilities(team_a, team_b):
    if is_tbd_team(team_a) or is_tbd_team(team_b):
        return None
    return FALLBACK_PROBS


def sample_three_way_result(prob_loss, prob_draw, prob_win, rng) -> str:
    probs = normalize_probabilities(prob_loss, prob_draw, prob_win) or FALLBACK_PROBS
    return rng.choice(["team_a_loss", "draw", "team_a_win"], p=probs)


def convert_three_way_to_advancement_probability(row) -> tuple[float | None, float | None]:
    probs = normalize_probabilities(row.get("prob_team_a_loss"), row.get("prob_draw"), row.get("prob_team_a_win"))
    if probs is None:
        probs = fallback_match_probabilities(row.get("team_a"), row.get("team_b"))
    if probs is None:
        return None, None
    prob_loss, prob_draw, prob_win = probs
    team_a_adv = prob_win + 0.5 * prob_draw
    team_b_adv = prob_loss + 0.5 * prob_draw
    total = team_a_adv + team_b_adv
    return team_a_adv / total, team_b_adv / total


def sample_match_winner(row, rng, allow_draw: bool = True) -> dict:
    probs = normalize_probabilities(row.get("prob_team_a_loss"), row.get("prob_draw"), row.get("prob_team_a_win"))
    used_fallback = False
    if probs is None:
        probs = fallback_match_probabilities(row.get("team_a"), row.get("team_b"))
        used_fallback = probs is not None
    if probs is None:
        return {"simulatable": False, "used_fallback": False}
    if allow_draw:
        result = rng.choice(["team_a_loss", "draw", "team_a_win"], p=probs)
        advancing = None
    else:
        team_a_adv, team_b_adv = convert_three_way_to_advancement_probability(row)
        result = "team_a_win" if rng.random() < team_a_adv else "team_a_loss"
        advancing = row.get("team_a") if result == "team_a_win" else row.get("team_b")
    return {
        "simulatable": True,
        "result_label": result,
        "advancing_team": advancing,
        "used_fallback": used_fallback,
    }
