"""Conservative knockout-stage simulation."""

from __future__ import annotations

import pandas as pd

from src.simulation.bracket_mapping import get_dynamic_match_probabilities, propagate_knockout_winner
from src.simulation.match_sampler import convert_three_way_to_advancement_probability, sample_match_winner
from src.simulation.tournament_structure import is_tbd_team


def simulate_known_knockout_fixtures(knockout_fixtures_df: pd.DataFrame, rng) -> dict:
    winners = []
    match_results = []
    unresolved = 0
    fallback_count = 0
    for _, row in knockout_fixtures_df.iterrows():
        if is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")):
            unresolved += 1
            continue
        result = sample_match_winner(row, rng, allow_draw=False)
        if not result.get("simulatable"):
            unresolved += 1
            continue
        fallback_count += int(result.get("used_fallback", False))
        winners.append(result["advancing_team"])
        match_results.append(
            {
                "match_id": row.get("match_id"),
                "stage": row.get("stage"),
                "team_a": row.get("team_a"),
                "team_b": row.get("team_b"),
                "result_label": result.get("result_label"),
                "advancing_team": result.get("advancing_team"),
            }
        )
    return {"winners": winners, "match_results": match_results, "unresolved": unresolved, "fallback_count": fallback_count}


def resolve_tbd_knockout_placeholders(knockout_fixtures_df: pd.DataFrame, simulated_advancers) -> pd.DataFrame:
    return knockout_fixtures_df.copy()


def simulate_knockout_bracket(knockout_fixtures_df: pd.DataFrame, rng) -> dict:
    result = simulate_known_knockout_fixtures(knockout_fixtures_df, rng)
    return {**result, "champion": None, "full_champion_simulation_possible": False}


def convert_three_way_to_advancement_probability_for_row(row):
    return convert_three_way_to_advancement_probability(row)


def simulate_knockout_round(round_matches_df: pd.DataFrame, rng, probability_lookup: dict, team_ratings_df: pd.DataFrame | None = None) -> dict:
    rows = []
    source_counts = {"model_exact": 0, "model_reversed": 0, "elo_fallback": 0, "neutral_fallback": 0}
    unresolved = 0
    for _, row in round_matches_df.iterrows():
        team_a = row.get("team_a")
        team_b = row.get("team_b")
        if is_tbd_team(team_a) or is_tbd_team(team_b):
            unresolved += 1
            continue
        probs, source = get_dynamic_match_probabilities(team_a, team_b, probability_lookup, team_ratings_df)
        source_counts[source] = source_counts.get(source, 0) + 1
        loss, draw, win = probs
        team_a_adv = win + 0.5 * draw
        team_b_adv = loss + 0.5 * draw
        total = team_a_adv + team_b_adv
        team_a_adv = team_a_adv / total
        result_label = "team_a_win" if rng.random() < team_a_adv else "team_a_loss"
        winner = team_a if result_label == "team_a_win" else team_b
        loser = team_b if result_label == "team_a_win" else team_a
        rows.append({"stage": row.get("stage"), "match_slot": row.get("match_slot"), "team_a": team_a, "team_b": team_b, "winner": winner, "loser": loser, "result_label": result_label, "probability_source": source})
    return {"results": rows, "source_counts": source_counts, "unresolved": unresolved}


def simulate_full_knockout_bracket(round_of_32_df: pd.DataFrame, progression_df: pd.DataFrame, rng, probability_lookup: dict, team_ratings_df: pd.DataFrame | None = None) -> dict:
    bracket_state = round_of_32_df.copy()
    stages = ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final"]
    all_results = []
    source_counts = {"model_exact": 0, "model_reversed": 0, "elo_fallback": 0, "neutral_fallback": 0}
    unresolved = 0
    champion = None
    reached = {}
    for stage in stages:
        round_matches = bracket_state[bracket_state["stage"].eq(stage)].copy()
        if round_matches.empty:
            unresolved += 1
            break
        if round_matches[["team_a", "team_b"]].isna().any().any():
            unresolved += int(round_matches[["team_a", "team_b"]].isna().any(axis=1).sum())
            break
        result = simulate_knockout_round(round_matches, rng, probability_lookup, team_ratings_df)
        unresolved += result["unresolved"]
        for key, value in result["source_counts"].items():
            source_counts[key] = source_counts.get(key, 0) + value
        for match in result["results"]:
            all_results.append(match)
            reached[match["winner"]] = _next_stage(stage)
            reached.setdefault(match["loser"], stage)
            if stage == "Final":
                champion = match["winner"]
            else:
                bracket_state = propagate_knockout_winner(bracket_state, match["winner"], match["match_slot"], progression_df)
    return {"champion": champion, "match_results": all_results, "team_reached_stage": reached, "unresolved": unresolved, "source_counts": source_counts, "full_bracket_completed": champion is not None and unresolved == 0}


def _next_stage(stage: str) -> str:
    order = ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Champion"]
    try:
        return order[order.index(stage) + 1]
    except Exception:
        return stage
