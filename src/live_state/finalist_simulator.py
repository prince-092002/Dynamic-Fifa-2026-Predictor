"""Live finalist and champion simulation from the current tournament state."""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR, OUTPUTS_DIR
from src.live_state.live_config import LIVE_STATE_DIR, RANDOM_SEED, coerce_bool_series, ensure_live_directories
from src.simulation.bracket_mapping import build_probability_lookup, get_dynamic_match_probabilities, load_bracket_slots, load_round_progression
from src.simulation.third_place_rules import assign_best_third_place_slots, select_best_third_place_teams
from src.simulation.tournament_simulator import (
    _build_fast_round_of_32,
    _prepare_progression_map,
    _prepare_r32_slot_records,
    _rating_map_from_frame,
    _simulate_fast_full_knockout,
)
from src.simulation.tournament_structure import is_tbd_team
from src.utils.dates import now_utc_iso


def _read(path, columns=None) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns or [])


def _group_code(value) -> str:
    text = str(value or "").strip()
    normalized = text.replace("_", " ")
    return normalized.split()[-1].upper() if normalized.lower().startswith("group ") else text


def _probability_rows_from_fixture(fixtures: pd.DataFrame, predictions: pd.DataFrame, ratings: pd.DataFrame, live_probability_lookup: dict | None = None) -> pd.DataFrame:
    prediction_by_match = {str(row["match_id"]): row for _, row in predictions.iterrows()} if not predictions.empty and "match_id" in predictions else {}
    probability_lookup = build_probability_lookup(predictions) if not predictions.empty else {}
    live_lookup = live_probability_lookup or {}
    rating_map = _rating_map_from_frame(ratings)
    rows = []
    for _, fixture in fixtures.iterrows():
        team_a = fixture.get("team_a")
        team_b = fixture.get("team_b")
        match_id = str(fixture.get("match_id", ""))
        is_completed = str(fixture.get("status", "")).lower() in {"completed", "finished", "ft", "match finished", "aet", "pen"} or _bool_value(fixture.get("is_completed", False))
        source = "completed_result"
        loss = draw = win = pd.NA
        if is_completed:
            ga = pd.to_numeric(fixture.get("team_a_goals"), errors="coerce")
            gb = pd.to_numeric(fixture.get("team_b_goals"), errors="coerce")
            if pd.notna(ga) and pd.notna(gb):
                loss, draw, win = (1.0, 0.0, 0.0) if ga < gb else (0.0, 1.0, 0.0) if ga == gb else (0.0, 0.0, 1.0)
        elif (str(team_a), str(team_b)) in live_lookup:
            loss, draw, win = live_lookup[(str(team_a), str(team_b))]
            source = "live_model_exact"
        elif (str(team_b), str(team_a)) in live_lookup:
            win, draw, loss = live_lookup[(str(team_b), str(team_a))]
            source = "live_model_reversed"
        elif match_id in prediction_by_match and str(prediction_by_match[match_id].get("prediction_status")) == "predicted":
            pred = prediction_by_match[match_id]
            loss, draw, win = pred["prob_team_a_loss"], pred["prob_draw"], pred["prob_team_a_win"]
            source = "model_prediction_file"
        elif not is_tbd_team(team_a) and not is_tbd_team(team_b):
            (loss, draw, win), source = get_dynamic_match_probabilities(team_a, team_b, probability_lookup, rating_map)
        else:
            source = "unresolved_tbd"
        if pd.notna(loss) and pd.notna(draw) and pd.notna(win):
            team_a_adv = float(win) + 0.5 * float(draw)
            team_b_adv = float(loss) + 0.5 * float(draw)
        else:
            team_a_adv = pd.NA
            team_b_adv = pd.NA
        rows.append(
            {
                "match_id": fixture.get("match_id"),
                "fixture_id": fixture.get("fixture_id", fixture.get("match_id")),
                "stage": fixture.get("stage"),
                "team_a": team_a,
                "team_b": team_b,
                "prob_team_a_loss": loss,
                "prob_draw": draw,
                "prob_team_a_win": win,
                "prob_team_a_advance": team_a_adv,
                "prob_team_b_advance": team_b_adv,
                "probability_source": source,
                "is_completed": is_completed,
                "is_simulated": not is_completed and source != "unresolved_tbd",
                "last_updated": now_utc_iso(),
            }
        )
    return pd.DataFrame(rows)


def get_remaining_match_probabilities(current_state=None, selected_model=None, feature_pipeline_outputs=None) -> pd.DataFrame:
    ensure_live_directories()
    live_path = LIVE_STATE_DIR / "live_fixtures_normalized.csv"
    fixtures = _read(live_path)
    if fixtures.empty:
        fixtures = _read(PROCESSED_DIR / "fixtures_2026.csv")
    predictions = _read(OUTPUTS_DIR / "predictions" / "fixture_2026_match_predictions.csv")
    ratings = _read(PROCESSED_DIR / "team_ratings.csv")
    probs = _probability_rows_from_fixture(fixtures, predictions, ratings, _load_live_prediction_lookup())
    path = LIVE_STATE_DIR / "remaining_match_probabilities.csv"
    probs.to_csv(path, index=False)
    return probs


def _load_live_prediction_lookup() -> dict:
    from src.live_state.live_matchup_predictor import load_live_knockout_prediction_lookup

    return load_live_knockout_prediction_lookup()


def _initial_standing(team: str, group: str) -> dict:
    return {"team": team, "group": group, "points": 0, "goal_difference": 0, "goals_for": 0, "played": 0}


def _apply_match_to_standings(standings: dict, group: str, team_a: str, team_b: str, result_label: str) -> None:
    a = standings.setdefault((group, team_a), _initial_standing(team_a, group))
    b = standings.setdefault((group, team_b), _initial_standing(team_b, group))
    a["played"] += 1
    b["played"] += 1
    if result_label == "team_a_win":
        a["points"] += 3
        a["goal_difference"] += 1
        b["goal_difference"] -= 1
        a["goals_for"] += 1
    elif result_label == "team_a_loss":
        b["points"] += 3
        b["goal_difference"] += 1
        a["goal_difference"] -= 1
        b["goals_for"] += 1
    else:
        a["points"] += 1
        b["points"] += 1


def _prepare_group_records(fixtures: pd.DataFrame, probabilities: pd.DataFrame) -> list[dict]:
    prob_map = {str(row["match_id"]): row for _, row in probabilities.iterrows()}
    stage = fixtures["stage"] if "stage" in fixtures else pd.Series("", index=fixtures.index)
    group_matches = fixtures[stage.astype(str).str.contains("Group", case=False, na=False)].copy()
    records = []
    for _, row in group_matches.iterrows():
        prob = prob_map.get(str(row.get("match_id")))
        probs = None
        fixed_result = None
        if prob is not None and pd.notna(prob.get("prob_team_a_loss")):
            probs = (float(prob["prob_team_a_loss"]), float(prob["prob_draw"]), float(prob["prob_team_a_win"]))
            if _bool_value(prob.get("is_completed", False)):
                fixed_result = "team_a_win" if probs[2] == 1 else "team_a_loss" if probs[0] == 1 else "draw"
        records.append(
            {
                "group": _group_code(row.get("group") or row.get("stage")),
                "team_a": row.get("team_a"),
                "team_b": row.get("team_b"),
                "team_a_is_tbd": is_tbd_team(row.get("team_a")),
                "team_b_is_tbd": is_tbd_team(row.get("team_b")),
                "probs": probs,
                "fixed_result": fixed_result,
            }
        )
    return records


def _simulate_group_stage(group_records: list[dict], rng) -> tuple[pd.DataFrame, list[dict]]:
    standings: dict[tuple[str, str], dict] = {}
    results = []
    for row in group_records:
        group = _group_code(row.get("group") or row.get("stage"))
        team_a = row.get("team_a")
        team_b = row.get("team_b")
        if not row["team_a_is_tbd"]:
            standings.setdefault((group, team_a), _initial_standing(team_a, group))
        if not row["team_b_is_tbd"]:
            standings.setdefault((group, team_b), _initial_standing(team_b, group))
        if row["team_a_is_tbd"] or row["team_b_is_tbd"] or row["probs"] is None:
            continue
        if row["fixed_result"]:
            result_label = row["fixed_result"]
        else:
            result_label = rng.choice(["team_a_loss", "draw", "team_a_win"], p=row["probs"])
        _apply_match_to_standings(standings, group, team_a, team_b, result_label)
        results.append({"stage": "Group Stage", "team_a": team_a, "team_b": team_b, "result_label": result_label})
    standings_df = pd.DataFrame(standings.values())
    ranked = []
    for group, group_df in standings_df.groupby("group", sort=True) if not standings_df.empty else []:
        ordered = group_df.sort_values(["points", "goal_difference", "goals_for", "team"], ascending=[False, False, False, True]).copy()
        ordered["group_rank"] = range(1, len(ordered) + 1)
        ranked.append(ordered)
    return (pd.concat(ranked, ignore_index=True) if ranked else pd.DataFrame(), results)


KNOCKOUT_STAGE_ORDER = ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final"]
NEXT_KNOCKOUT_STAGE = {
    "Round of 32": "Round of 16",
    "Round of 16": "Quarterfinal",
    "Quarterfinal": "Semifinal",
    "Semifinal": "Final",
}
EXPECTED_STAGE_ROWS = {"Round of 32": 16, "Round of 16": 8, "Quarterfinal": 4, "Semifinal": 2, "Final": 1}


def _simulate_live_bracket_forward(bracket: pd.DataFrame, rng, probability_lookup: dict, rating_map: dict, live_lookup: dict | None = None) -> dict | None:
    if bracket.empty:
        return None
    data = bracket.copy()
    data = data[data["stage"].astype(str).isin(KNOCKOUT_STAGE_ORDER)]
    if data.empty:
        return None
    start_stage = None
    start_rows = pd.DataFrame()
    for stage in reversed(KNOCKOUT_STAGE_ORDER):
        rows = data[data["stage"].astype(str).eq(stage)].copy()
        rows = rows[rows.apply(lambda row: _known_team(row.get("team_a")) and _known_team(row.get("team_b")), axis=1)]
        if len(rows) >= EXPECTED_STAGE_ROWS[stage]:
            start_stage = stage
            start_rows = rows.head(EXPECTED_STAGE_ROWS[stage]).copy()
            break
    if start_stage is None:
        return None

    current_stage = start_stage
    current_matches = start_rows.to_dict(orient="records")
    all_results = []
    semifinalists = []
    finalists = []
    while current_matches:
        winners = []
        next_rows = []
        for row in current_matches:
            winner, loser, result_label, source = _simulate_or_lock_knockout_match(row, rng, probability_lookup, rating_map, live_lookup)
            if winner is None:
                return None
            winners.append(winner)
            all_results.append(
                {
                    "stage": current_stage,
                    "team_a": row.get("team_a"),
                    "team_b": row.get("team_b"),
                    "winner": winner,
                    "loser": loser,
                    "result_label": result_label,
                    "probability_source": source,
                }
            )
        if current_stage == "Quarterfinal":
            semifinalists = winners.copy()
        if current_stage == "Semifinal":
            finalists = winners.copy()
        if current_stage == "Final":
            final = all_results[-1]
            return {
                "finalist_1": final["team_a"],
                "finalist_2": final["team_b"],
                "champion": final["winner"],
                "runner_up": final["loser"],
                "semifinalists": semifinalists,
                "match_results": all_results,
            }
        next_stage = NEXT_KNOCKOUT_STAGE[current_stage]
        for index in range(0, len(winners), 2):
            if index + 1 >= len(winners):
                return None
            next_rows.append({"stage": next_stage, "team_a": winners[index], "team_b": winners[index + 1], "is_completed": False, "winner": ""})
        current_stage = next_stage
        current_matches = next_rows
    return None


def _simulate_or_lock_knockout_match(row: dict, rng, probability_lookup: dict, rating_map: dict, live_lookup: dict | None = None) -> tuple[object | None, object | None, str, str]:
    team_a = row.get("team_a")
    team_b = row.get("team_b")
    if not _known_team(team_a) or not _known_team(team_b):
        return None, None, "unresolved_tbd", "unresolved_tbd"
    winner = row.get("winner")
    if _bool_value(row.get("is_completed", False)) and _known_team(winner):
        loser = team_b if str(winner) == str(team_a) else team_a
        return winner, loser, "completed_result", "completed_result"
    probs, source = get_dynamic_match_probabilities(team_a, team_b, probability_lookup, rating_map, live_probability_lookup=live_lookup)
    loss, draw, win = probs
    team_a_adv = win + 0.5 * draw
    team_b_adv = loss + 0.5 * draw
    team_a_adv = team_a_adv / (team_a_adv + team_b_adv)
    result_label = "team_a_win" if rng.random() < team_a_adv else "team_a_loss"
    winner = team_a if result_label == "team_a_win" else team_b
    loser = team_b if result_label == "team_a_win" else team_a
    return winner, loser, result_label, source


def _known_team(value) -> bool:
    return pd.notna(value) and not is_tbd_team(value)


def _simulate_known_semis_or_final(bracket: pd.DataFrame, rng, probability_lookup: dict, rating_map: dict, live_lookup: dict | None = None) -> dict | None:
    if bracket.empty:
        return None
    final_rows = bracket[bracket["stage"].astype(str).eq("Final")]
    if not final_rows.empty and not is_tbd_team(final_rows.iloc[0].get("team_a")) and not is_tbd_team(final_rows.iloc[0].get("team_b")):
        row = final_rows.iloc[0]
        team_a, team_b = row["team_a"], row["team_b"]
        if _bool_value(row.get("is_completed", False)) and row.get("winner"):
            champion = row["winner"]
        else:
            probs, _ = get_dynamic_match_probabilities(team_a, team_b, probability_lookup, rating_map, live_probability_lookup=live_lookup)
            loss, draw, win = probs
            champion = team_a if rng.random() < (win + 0.5 * draw) else team_b
        runner = team_b if champion == team_a else team_a
        return {"finalist_1": team_a, "finalist_2": team_b, "champion": champion, "runner_up": runner, "semifinalists": [], "match_results": []}
    semis = bracket[bracket["stage"].astype(str).eq("Semifinal")]
    if len(semis) >= 2:
        finalists = []
        semifinalists = []
        for _, row in semis.head(2).iterrows():
            team_a, team_b = row.get("team_a"), row.get("team_b")
            if is_tbd_team(team_a) or is_tbd_team(team_b):
                return None
            semifinalists.extend([team_a, team_b])
            probs, _ = get_dynamic_match_probabilities(team_a, team_b, probability_lookup, rating_map, live_probability_lookup=live_lookup)
            loss, draw, win = probs
            finalists.append(team_a if rng.random() < (win + 0.5 * draw) else team_b)
        probs, _ = get_dynamic_match_probabilities(finalists[0], finalists[1], probability_lookup, rating_map, live_probability_lookup=live_lookup)
        loss, draw, win = probs
        champion = finalists[0] if rng.random() < (win + 0.5 * draw) else finalists[1]
        return {"finalist_1": finalists[0], "finalist_2": finalists[1], "champion": champion, "runner_up": finalists[1] if champion == finalists[0] else finalists[0], "semifinalists": semifinalists, "match_results": []}
    return None


def run_live_finalist_simulation(n_simulations: int = 10000, seed: int = RANDOM_SEED) -> dict:
    ensure_live_directories()
    if n_simulations <= 0:
        raise ValueError("n_simulations must be positive")
    fixtures = _read(LIVE_STATE_DIR / "live_fixtures_normalized.csv")
    if fixtures.empty:
        fixtures = _read(PROCESSED_DIR / "fixtures_2026.csv")
    probabilities = _read(LIVE_STATE_DIR / "remaining_match_probabilities.csv")
    if probabilities.empty:
        probabilities = get_remaining_match_probabilities()
    predictions = _read(OUTPUTS_DIR / "predictions" / "fixture_2026_match_predictions.csv")
    ratings = _read(PROCESSED_DIR / "team_ratings.csv")
    rating_map = _rating_map_from_frame(ratings)
    probability_lookup = build_probability_lookup(predictions) if not predictions.empty else {}
    live_lookup = _load_live_prediction_lookup()
    bracket = _read(LIVE_STATE_DIR / "merged_bracket_state.csv")
    slots = load_bracket_slots()
    progression = load_round_progression()
    r32_slot_records = _prepare_r32_slot_records(slots)
    progression_map = _prepare_progression_map(progression)
    group_records = _prepare_group_records(fixtures, probabilities)
    rng = np.random.default_rng(seed)
    rows = []
    match_sample = []
    source_counts = Counter()
    fallback_used = bracket.empty or bool((bracket.get("bracket_source", pd.Series(dtype=str)) == "fallback_template").any())
    for sim_id in range(1, n_simulations + 1):
        known_result = _simulate_live_bracket_forward(bracket, rng, probability_lookup, rating_map, live_lookup)
        if known_result is not None:
            outcome = known_result
            for match in outcome.get("match_results", []):
                source_counts[match.get("probability_source", "live_bracket_forward")] += 1
        else:
            standings, group_results = _simulate_group_stage(group_records, rng)
            best_thirds = select_best_third_place_teams(standings.rename(columns={"rank": "group_rank"}) if "group_rank" not in standings else standings)
            third_assignments = assign_best_third_place_slots(best_thirds, write_report=False)
            round32 = _build_fast_round_of_32(standings, r32_slot_records, third_assignments)
            knockout = _simulate_fast_full_knockout(round32, progression_map, rng, probability_lookup, rating_map)
            for key, value in knockout["source_counts"].items():
                source_counts[key] += value
            final_rows = [row for row in knockout["match_results"] if row["stage"] == "Final"]
            final = final_rows[0] if final_rows else {}
            semis = [row for row in knockout["match_results"] if row["stage"] == "Semifinal"]
            outcome = {
                "finalist_1": final.get("team_a"),
                "finalist_2": final.get("team_b"),
                "champion": knockout.get("champion"),
                "runner_up": final.get("loser"),
                "semifinalists": sorted({team for row in semis for team in [row.get("team_a"), row.get("team_b")] if team}),
                "match_results": group_results + knockout["match_results"],
            }
        finalists = sorted([team for team in [outcome.get("finalist_1"), outcome.get("finalist_2")] if pd.notna(team)])
        rows.append(
            {
                "simulation_id": sim_id,
                "finalist_1": outcome.get("finalist_1"),
                "finalist_2": outcome.get("finalist_2"),
                "finalist_pair_key": " vs ".join(finalists),
                "champion": outcome.get("champion"),
                "runner_up": outcome.get("runner_up"),
                "semifinalists": "; ".join(outcome.get("semifinalists", [])),
                "fallback_mapping_used": fallback_used,
            }
        )
        if sim_id <= 25:
            for match in outcome.get("match_results", [])[:80]:
                match_sample.append({"simulation_id": sim_id, **match})
    result_df = pd.DataFrame(rows)
    sample_df = pd.DataFrame(match_sample)
    result_path = LIVE_STATE_DIR / "live_finalist_simulation_results.csv"
    sample_path = LIVE_STATE_DIR / "live_simulated_match_results_sample.csv"
    result_df.to_csv(result_path, index=False)
    sample_df.to_csv(sample_path, index=False)
    counts_path = LIVE_STATE_DIR / "live_probability_source_counts.json"
    if counts_path.exists():
        (LIVE_STATE_DIR / "live_probability_source_counts_previous.json").write_text(counts_path.read_text(encoding="utf-8"), encoding="utf-8")
    counts_path.write_text(json.dumps(dict(source_counts), indent=2), encoding="utf-8")
    return {"results": result_df, "sample": sample_df, "results_path": str(result_path), "sample_path": str(sample_path), "source_counts": dict(source_counts), "fallback_mapping_used": fallback_used}


def _bool_value(value) -> bool:
    return bool(coerce_bool_series(pd.Series([value])).iloc[0])
