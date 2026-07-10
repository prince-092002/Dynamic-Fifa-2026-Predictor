"""Monte Carlo tournament simulation runner."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR
from src.simulation.bracket_config import THIRD_PLACE_MAPPING_PATH
from src.simulation.bracket_mapping import build_probability_lookup, create_default_bracket_files, get_dynamic_match_probabilities, load_bracket_slots, load_round_progression
from src.simulation.knockout_stage import simulate_full_knockout_bracket
from src.simulation.third_place_rules import assign_best_third_place_slots, select_best_third_place_teams
from src.simulation.data_loader import load_simulation_inputs
from src.simulation.match_sampler import normalize_probabilities
from src.simulation.simulation_config import DEFAULT_N_SIMULATIONS, RANDOM_SEED, normalize_stage
from src.simulation.tournament_structure import is_tbd_team


def _prepare_simulation_fixture_records(predictions: pd.DataFrame) -> dict:
    data = predictions.copy()
    data["normalized_stage"] = data.get("stage", pd.Series("", index=data.index)).apply(normalize_stage)
    group_records = []
    knockout_records = []
    known_group_teams = set()
    for _, row in data.iterrows():
        record = {
            "match_id": row.get("match_id"),
            "stage": row.get("normalized_stage"),
            "group": row.get("group"),
            "team_a": row.get("team_a"),
            "team_b": row.get("team_b"),
            "probs": normalize_probabilities(row.get("prob_team_a_loss"), row.get("prob_draw"), row.get("prob_team_a_win")),
            "team_a_is_tbd": is_tbd_team(row.get("team_a")),
            "team_b_is_tbd": is_tbd_team(row.get("team_b")),
        }
        record["is_tbd"] = record["team_a_is_tbd"] or record["team_b_is_tbd"]
        if record["stage"] == "Group Stage":
            group_records.append(record)
            if not record["team_a_is_tbd"]:
                known_group_teams.add(str(record["team_a"]))
            if not record["team_b_is_tbd"]:
                known_group_teams.add(str(record["team_b"]))
        else:
            knockout_records.append(record)
    return {"group_records": group_records, "knockout_records": knockout_records, "known_group_teams": sorted(known_group_teams)}


def _empty_standing(team: str, group: str) -> dict:
    return {"team": team, "group": group, "points": 0, "wins": 0, "draws": 0, "losses": 0, "gd": 0, "gf": 0}


def _group_code(value) -> str:
    text = str(value or "").strip()
    normalized = text.replace("_", " ")
    return normalized.split()[-1].upper() if normalized.lower().startswith("group ") else text


def _slot_sort_key(match_slot: str) -> tuple[str, int]:
    prefix, _, number = str(match_slot).partition("_M")
    try:
        return prefix, int(number)
    except ValueError:
        return prefix, 0


def _simulate_prepared_group_stage(group_records: list[dict], rng) -> dict:
    standings: dict[tuple[str, str], dict] = {}
    match_results = []
    unresolved = 0
    for record in group_records:
        group = _group_code(record["group"])
        if not record["team_a_is_tbd"]:
            team_a = str(record["team_a"])
            standings.setdefault((group, team_a), _empty_standing(team_a, group))
        if not record["team_b_is_tbd"]:
            team_b = str(record["team_b"])
            standings.setdefault((group, team_b), _empty_standing(team_b, group))
        if record["is_tbd"] or record["probs"] is None:
            unresolved += 1
            continue
        team_a = str(record["team_a"])
        team_b = str(record["team_b"])
        standings.setdefault((group, team_a), _empty_standing(team_a, group))
        standings.setdefault((group, team_b), _empty_standing(team_b, group))
        result = rng.choice(["team_a_loss", "draw", "team_a_win"], p=record["probs"])
        if result == "team_a_win":
            standings[(group, team_a)]["points"] += 3
            standings[(group, team_a)]["wins"] += 1
            standings[(group, team_b)]["losses"] += 1
            standings[(group, team_a)]["gd"] += 1
            standings[(group, team_b)]["gd"] -= 1
            standings[(group, team_a)]["gf"] += 1
        elif result == "team_a_loss":
            standings[(group, team_b)]["points"] += 3
            standings[(group, team_b)]["wins"] += 1
            standings[(group, team_a)]["losses"] += 1
            standings[(group, team_b)]["gd"] += 1
            standings[(group, team_a)]["gd"] -= 1
            standings[(group, team_b)]["gf"] += 1
        else:
            standings[(group, team_a)]["points"] += 1
            standings[(group, team_b)]["points"] += 1
            standings[(group, team_a)]["draws"] += 1
            standings[(group, team_b)]["draws"] += 1
        match_results.append({"match_id": record["match_id"], "stage": "Group Stage", "team_a": team_a, "team_b": team_b, "result_label": result})
    advancers = []
    standings_output = []
    if standings:
        by_group: dict[str, list[dict]] = {}
        for record in standings.values():
            by_group.setdefault(record["group"], []).append(record)
        for group_records in by_group.values():
            ranked = sorted(
                group_records,
                key=lambda item: (item["points"], item["gd"], item["gf"], rng.random()),
                reverse=True,
            )
            for rank, item in enumerate(ranked, start=1):
                standings_output.append(
                    {
                        "team": item["team"],
                        "group": item["group"],
                        "points": item["points"],
                        "goal_difference": item["gd"],
                        "goals_for": item["gf"],
                        "group_rank": rank,
                    }
                )
            advancers.extend([item["team"] for item in ranked[:2]])
    return {"advancers": advancers, "standings": pd.DataFrame(standings_output), "match_results": match_results, "unresolved": unresolved}


def _simulate_prepared_knockout(knockout_records: list[dict], rng) -> dict:
    winners = []
    match_results = []
    unresolved = 0
    for record in knockout_records:
        if record["is_tbd"] or record["probs"] is None:
            unresolved += 1
            continue
        loss, draw, win = record["probs"]
        team_a_adv = win + 0.5 * draw
        team_b_adv = loss + 0.5 * draw
        total = team_a_adv + team_b_adv
        team_a_adv = team_a_adv / total
        result = "team_a_win" if rng.random() < team_a_adv else "team_a_loss"
        winner = record["team_a"] if result == "team_a_win" else record["team_b"]
        winners.append(winner)
        match_results.append({"match_id": record["match_id"], "stage": record["stage"], "team_a": record["team_a"], "team_b": record["team_b"], "result_label": result, "advancing_team": winner})
    return {"winners": winners, "match_results": match_results, "unresolved": unresolved}


def _prepare_r32_slot_records(slots: pd.DataFrame) -> list[dict]:
    records = []
    for match_slot, slot_df in slots.groupby("match_slot", sort=False):
        item = {"match_slot": match_slot, "stage": "Round of 32", "team_a": None, "team_b": None}
        for _, slot in slot_df.iterrows():
            item[slot["team_slot"]] = {
                "qualifier_type": slot["qualifier_type"],
                "group": str(slot.get("group", "")),
                "placement": slot.get("placement"),
                "third_place_mapping_key": slot.get("third_place_mapping_key"),
            }
        records.append(item)
    return records


def _prepare_progression_map(progression: pd.DataFrame) -> dict:
    return {
        row["from_match_slot"]: {
            "stage": row["winner_feeds_to_stage"],
            "match_slot": row["winner_feeds_to_match_slot"],
            "team_slot": row["winner_feeds_to_team_slot"],
        }
        for _, row in progression.iterrows()
    }


def _rating_map_from_frame(ratings: pd.DataFrame) -> dict:
    if ratings.empty:
        return {}
    values = ratings["elo_rating"].where(ratings["elo_rating"].notna(), ratings["fifa_points"]) if "elo_rating" in ratings.columns else ratings["fifa_points"]
    return dict(zip(ratings["team"], pd.to_numeric(values, errors="coerce")))


def _resolve_slot_team(slot: dict, standings_map: dict, third_map: dict):
    if slot["qualifier_type"] in {"group_winner", "group_runner_up"}:
        return standings_map.get((slot["group"], int(float(slot["placement"]))))
    if slot["qualifier_type"] == "best_third_place":
        return third_map.get(slot["third_place_mapping_key"])
    return None


def _build_fast_round_of_32(standings: pd.DataFrame, slot_records: list[dict], third_assignments: pd.DataFrame) -> list[dict]:
    standings_map = {
        (str(row["group"]), int(row["group_rank"])): row["team"]
        for _, row in standings.iterrows()
    }
    third_map = dict(zip(third_assignments["third_place_mapping_key"], third_assignments["team"]))
    matches = []
    for record in slot_records:
        team_a = _resolve_slot_team(record["team_a"], standings_map, third_map)
        team_b = _resolve_slot_team(record["team_b"], standings_map, third_map)
        matches.append({"stage": "Round of 32", "match_slot": record["match_slot"], "team_a": team_a, "team_b": team_b})
    return matches


def _simulate_fast_full_knockout(round32_matches: list[dict], progression_map: dict, rng, probability_lookup: dict, team_ratings: dict) -> dict:
    current_matches = round32_matches
    all_results = []
    source_counts = {"model_exact": 0, "model_reversed": 0, "elo_fallback": 0, "neutral_fallback": 0}
    unresolved = 0
    champion = None
    reached = {}
    while current_matches:
        next_matches = {}
        for match in current_matches:
            team_a = match.get("team_a")
            team_b = match.get("team_b")
            if is_tbd_team(team_a) or is_tbd_team(team_b):
                unresolved += 1
                continue
            probs, source = get_dynamic_match_probabilities(team_a, team_b, probability_lookup, team_ratings)
            source_counts[source] = source_counts.get(source, 0) + 1
            loss, draw, win = probs
            team_a_adv = win + 0.5 * draw
            team_b_adv = loss + 0.5 * draw
            team_a_adv = team_a_adv / (team_a_adv + team_b_adv)
            result_label = "team_a_win" if rng.random() < team_a_adv else "team_a_loss"
            winner = team_a if result_label == "team_a_win" else team_b
            loser = team_b if result_label == "team_a_win" else team_a
            all_results.append({**match, "winner": winner, "loser": loser, "result_label": result_label, "probability_source": source})
            target = progression_map.get(match["match_slot"])
            if target is None:
                champion = winner
                reached[winner] = "Champion"
                reached.setdefault(loser, match["stage"])
                continue
            reached[winner] = target["stage"]
            reached.setdefault(loser, match["stage"])
            next_match = next_matches.setdefault(target["match_slot"], {"stage": target["stage"], "match_slot": target["match_slot"], "team_a": None, "team_b": None})
            next_match[target["team_slot"]] = winner
        current_matches = [next_matches[key] for key in sorted(next_matches, key=_slot_sort_key)]
        if any(match["team_a"] is None or match["team_b"] is None for match in current_matches):
            unresolved += sum(1 for match in current_matches if match["team_a"] is None or match["team_b"] is None)
            break
    return {"champion": champion, "match_results": all_results, "team_reached_stage": reached, "unresolved": unresolved, "source_counts": source_counts, "full_bracket_completed": champion is not None and unresolved == 0}


def run_single_simulation(simulation_id: int, inputs: dict, rng) -> dict:
    prepared = inputs.get("prepared") or _prepare_simulation_fixture_records(inputs["predictions"])
    group_result = _simulate_prepared_group_stage(prepared["group_records"], rng)
    knockout_result = _simulate_prepared_knockout(prepared["knockout_records"], rng)
    team_stage_rows = []
    known_group_teams = prepared["known_group_teams"]
    advancers = set(group_result["advancers"])
    knockout_winners = set(knockout_result["winners"])
    for team in known_group_teams:
        deepest = "Round of 32" if team in advancers else "Group Stage"
        if team in knockout_winners:
            deepest = "Advanced From Known Knockout"
        team_stage_rows.append({"simulation_id": simulation_id, "team": team, "deepest_stage": deepest, "champion": False})
    return {
        "simulation_id": simulation_id,
        "team_stage_results": team_stage_rows,
        "match_results": group_result["match_results"] + knockout_result["match_results"],
        "champion": knockout_result.get("champion"),
        "unresolved_count": group_result["unresolved"] + knockout_result["unresolved"],
        "used_fallback_count": 0,
        "full_champion_simulation_possible": False,
    }


def run_monte_carlo_simulations(n_simulations: int = DEFAULT_N_SIMULATIONS, seed: int = RANDOM_SEED, inputs: dict | None = None) -> dict:
    if n_simulations <= 0:
        raise ValueError("n_simulations must be positive")
    inputs = inputs or load_simulation_inputs()
    inputs["prepared"] = _prepare_simulation_fixture_records(inputs["predictions"])
    rng = np.random.default_rng(seed)
    simulations = []
    for simulation_id in range(1, n_simulations + 1):
        simulations.append(run_single_simulation(simulation_id, inputs, rng))
    return {"simulations": simulations, "n_simulations": n_simulations, "seed": seed}


def run_single_full_bracket_simulation(simulation_id: int, inputs: dict, rng) -> dict:
    prepared = inputs.get("prepared") or _prepare_simulation_fixture_records(inputs["predictions"])
    group_result = _simulate_prepared_group_stage(prepared["group_records"], rng)
    standings = group_result["standings"]
    source_counts = {"model_exact": 0, "model_reversed": 0, "elo_fallback": 0, "neutral_fallback": 0}
    if standings.empty:
        return {"simulation_id": simulation_id, "champion": None, "full_bracket_completed": False, "unresolved_count": 32, "probability_source_counts": source_counts, "team_stage_results": [], "match_results": group_result["match_results"]}
    slots = inputs["bracket_slots"]
    progression = inputs["round_progression"]
    best_thirds = select_best_third_place_teams(standings)
    third_assignments = assign_best_third_place_slots(best_thirds, inputs["third_place_mapping"], write_report=False)
    round32 = _build_fast_round_of_32(standings, inputs["r32_slot_records"], third_assignments)
    knockout = _simulate_fast_full_knockout(round32, inputs["progression_map"], rng, inputs["probability_lookup"], inputs["team_ratings"])
    for key, value in knockout["source_counts"].items():
        source_counts[key] = source_counts.get(key, 0) + value
    reached = {}
    for _, row in standings.iterrows():
        if row["group_rank"] == 1:
            reached[row["team"]] = "Round of 32"
        elif row["group_rank"] == 2:
            reached[row["team"]] = "Round of 32"
        elif row["team"] in set(third_assignments.get("team", [])):
            reached[row["team"]] = "Round of 32"
        else:
            reached[row["team"]] = "Group Stage"
    reached.update(knockout["team_reached_stage"])
    if knockout["champion"]:
        reached[knockout["champion"]] = "Champion"
    team_rows = [{"simulation_id": simulation_id, "team": team, "deepest_stage": stage, "champion": team == knockout["champion"]} for team, stage in reached.items()]
    return {
        "simulation_id": simulation_id,
        "champion": knockout["champion"],
        "full_bracket_completed": knockout["full_bracket_completed"],
        "unresolved_count": group_result["unresolved"] + knockout["unresolved"],
        "probability_source_counts": source_counts,
        "team_stage_results": team_rows,
        "match_results": group_result["match_results"] + knockout["match_results"],
    }


def run_full_bracket_monte_carlo_simulations(n_simulations: int = DEFAULT_N_SIMULATIONS, seed: int = RANDOM_SEED, inputs: dict | None = None) -> dict:
    if n_simulations <= 0:
        raise ValueError("n_simulations must be positive")
    inputs = inputs or load_simulation_inputs()
    inputs["prepared"] = _prepare_simulation_fixture_records(inputs["predictions"])
    create_default_bracket_files(False)
    inputs["bracket_slots"] = load_bracket_slots()
    inputs["round_progression"] = load_round_progression()
    inputs["third_place_mapping"] = pd.read_csv(THIRD_PLACE_MAPPING_PATH)
    inputs["r32_slot_records"] = _prepare_r32_slot_records(inputs["bracket_slots"])
    inputs["progression_map"] = _prepare_progression_map(inputs["round_progression"])
    inputs["probability_lookup"] = build_probability_lookup(inputs["predictions"])
    ratings_path = PROCESSED_DIR / "team_ratings.csv"
    inputs["team_ratings"] = _rating_map_from_frame(pd.read_csv(ratings_path) if ratings_path.exists() else pd.DataFrame())
    rng = np.random.default_rng(seed)
    simulations = [run_single_full_bracket_simulation(sim_id, inputs, rng) for sim_id in range(1, n_simulations + 1)]
    return {"simulations": simulations, "n_simulations": n_simulations, "seed": seed, "mode": "full-bracket"}
