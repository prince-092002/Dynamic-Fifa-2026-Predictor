"""Group-stage simulation."""

from __future__ import annotations

import pandas as pd

from src.simulation.match_sampler import sample_match_winner
from src.simulation.simulation_config import GROUP_ADVANCER_RULES
from src.simulation.tournament_structure import is_tbd_team


def _empty_team_record(team: str, group: str) -> dict:
    return {"team": team, "group": group, "points": 0, "wins": 0, "draws": 0, "losses": 0, "goal_difference_simulated": 0, "goals_for_simulated": 0}


def simulate_group_match(row, rng) -> dict:
    sampled = sample_match_winner(row, rng, allow_draw=True)
    if not sampled.get("simulatable"):
        return {"simulatable": False, "used_fallback": False}
    result = sampled["result_label"]
    if result == "team_a_win":
        a_points, b_points, a_w, b_w, d = 3, 0, 1, 0, 0
        gd_a, gd_b = 1, -1
    elif result == "team_a_loss":
        a_points, b_points, a_w, b_w, d = 0, 3, 0, 1, 0
        gd_a, gd_b = -1, 1
    else:
        a_points, b_points, a_w, b_w, d = 1, 1, 0, 0, 1
        gd_a, gd_b = 0, 0
    return {
        "simulatable": True,
        "result_label": result,
        "team_a_points": a_points,
        "team_b_points": b_points,
        "team_a_win": a_w,
        "team_b_win": b_w,
        "draw": d,
        "team_a_goal_diff": gd_a,
        "team_b_goal_diff": gd_b,
        "used_fallback": sampled.get("used_fallback", False),
    }


def rank_group_teams(standings_df: pd.DataFrame, rng) -> pd.DataFrame:
    ranked = standings_df.copy()
    ranked["random_tiebreaker"] = rng.random(len(ranked))
    ranked = ranked.sort_values(
        ["points", "goal_difference_simulated", "goals_for_simulated", "random_tiebreaker"],
        ascending=[False, False, False, False],
    )
    ranked["group_rank"] = range(1, len(ranked) + 1)
    return ranked.drop(columns=["random_tiebreaker"])


def get_group_advancers(standings_df: pd.DataFrame, rules=GROUP_ADVANCER_RULES) -> list[str]:
    top_n = int(rules.get("top_n_per_group", 2))
    return standings_df[standings_df["group_rank"] <= top_n]["team"].tolist()


def simulate_group_stage(group_fixtures: pd.DataFrame, rng) -> dict:
    standings_by_group = []
    match_results = []
    advancers = []
    unresolved = 0
    fallback_count = 0
    for group, group_df in group_fixtures.groupby("group", dropna=False):
        records: dict[str, dict] = {}
        for _, row in group_df.iterrows():
            team_a = row.get("team_a")
            team_b = row.get("team_b")
            if is_tbd_team(team_a) or is_tbd_team(team_b):
                unresolved += 1
                continue
            records.setdefault(team_a, _empty_team_record(team_a, group))
            records.setdefault(team_b, _empty_team_record(team_b, group))
            result = simulate_group_match(row, rng)
            if not result.get("simulatable"):
                unresolved += 1
                continue
            fallback_count += int(result.get("used_fallback", False))
            records[team_a]["points"] += result["team_a_points"]
            records[team_b]["points"] += result["team_b_points"]
            records[team_a]["wins"] += result["team_a_win"]
            records[team_b]["wins"] += result["team_b_win"]
            records[team_a]["draws"] += result["draw"]
            records[team_b]["draws"] += result["draw"]
            records[team_a]["losses"] += result["team_b_win"]
            records[team_b]["losses"] += result["team_a_win"]
            records[team_a]["goal_difference_simulated"] += result["team_a_goal_diff"]
            records[team_b]["goal_difference_simulated"] += result["team_b_goal_diff"]
            records[team_a]["goals_for_simulated"] += max(result["team_a_goal_diff"], 0)
            records[team_b]["goals_for_simulated"] += max(result["team_b_goal_diff"], 0)
            match_results.append({"match_id": row.get("match_id"), "stage": "Group Stage", "team_a": team_a, "team_b": team_b, "result_label": result["result_label"]})
        if records:
            ranked = rank_group_teams(pd.DataFrame(records.values()), rng)
            standings_by_group.append(ranked)
            advancers.extend(get_group_advancers(ranked))
    standings = pd.concat(standings_by_group, ignore_index=True) if standings_by_group else pd.DataFrame()
    return {"standings": standings, "advancers": advancers, "match_results": match_results, "unresolved": unresolved, "fallback_count": fallback_count}
