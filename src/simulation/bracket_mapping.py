"""Explicit bracket mapping and dynamic probability helpers."""

from __future__ import annotations

import pandas as pd

from src.config import PROCESSED_DIR
from src.simulation.bracket_config import BRACKET_SLOTS_PATH, ROUND_PROGRESSION_PATH, THIRD_PLACE_MAPPING_PATH, GROUPS, ensure_bracket_directories
from src.simulation.bracket_reports import write_bracket_mapping_summary, write_bracket_source_report


def create_default_bracket_files(overwrite: bool = False) -> dict:
    ensure_bracket_directories()
    if overwrite or not BRACKET_SLOTS_PATH.exists():
        rows = []
        pairings = [
            ("A", 1, "B", 2),
            ("C", 1, "D", 2),
            ("E", 1, "F", 2),
            ("G", 1, "H", 2),
            ("I", 1, "J", 2),
            ("K", 1, "L", 2),
            ("B", 1, "A", 2),
            ("D", 1, "C", 2),
            ("F", 1, "E", 2),
            ("H", 1, "G", 2),
            ("J", 1, "I", 2),
            ("L", 1, "K", 2),
        ]
        for idx, (ga, pa, gb, pb) in enumerate(pairings, start=1):
            for team_slot, group, placement in [("team_a", ga, pa), ("team_b", gb, pb)]:
                qualifier = "group_winner" if placement == 1 else "group_runner_up"
                rows.append({"slot_id": f"R32_M{idx}_{team_slot}", "stage": "Round of 32", "match_slot": f"R32_M{idx}", "team_slot": team_slot, "qualifier_type": qualifier, "group": group, "placement": placement, "third_place_mapping_key": "", "notes": f"Fallback {qualifier} Group {group}"})
        third_pairs = [(1, 8), (2, 7), (3, 6), (4, 5)]
        for offset, (a, b) in enumerate(third_pairs, start=13):
            rows.append({"slot_id": f"R32_M{offset}_team_a", "stage": "Round of 32", "match_slot": f"R32_M{offset}", "team_slot": "team_a", "qualifier_type": "best_third_place", "group": "", "placement": "", "third_place_mapping_key": f"TP_SLOT_{a}", "notes": "Fallback best third-place rank slot"})
            rows.append({"slot_id": f"R32_M{offset}_team_b", "stage": "Round of 32", "match_slot": f"R32_M{offset}", "team_slot": "team_b", "qualifier_type": "best_third_place", "group": "", "placement": "", "third_place_mapping_key": f"TP_SLOT_{b}", "notes": "Fallback best third-place rank slot"})
        pd.DataFrame(rows).to_csv(BRACKET_SLOTS_PATH, index=False)
    if overwrite or not ROUND_PROGRESSION_PATH.exists():
        rows = []
        rounds = [("Round of 32", "R32", 16, "Round of 16", "R16"), ("Round of 16", "R16", 8, "Quarterfinal", "QF"), ("Quarterfinal", "QF", 4, "Semifinal", "SF"), ("Semifinal", "SF", 2, "Final", "FINAL")]
        for from_stage, from_prefix, count, to_stage, to_prefix in rounds:
            for i in range(1, count + 1):
                to_match = (i + 1) // 2
                team_slot = "team_a" if i % 2 == 1 else "team_b"
                rows.append({"from_stage": from_stage, "from_match_slot": f"{from_prefix}_M{i}", "winner_feeds_to_stage": to_stage, "winner_feeds_to_match_slot": f"{to_prefix}_M{to_match}", "winner_feeds_to_team_slot": team_slot, "notes": f"Winner feeds to {to_stage}"})
        pd.DataFrame(rows).to_csv(ROUND_PROGRESSION_PATH, index=False)
    if overwrite or not THIRD_PLACE_MAPPING_PATH.exists():
        pd.DataFrame([{"third_place_mapping_key": f"TP_SLOT_{i}", "rank_order": i, "mapping_source": "fallback_rank_order"} for i in range(1, 9)]).to_csv(THIRD_PLACE_MAPPING_PATH, index=False)
    slots = load_bracket_slots()
    progression = load_round_progression()
    return {"slots": str(BRACKET_SLOTS_PATH), "progression": str(ROUND_PROGRESSION_PATH), "third_place": str(THIRD_PLACE_MAPPING_PATH), "source_report": write_bracket_source_report(), "summary": write_bracket_mapping_summary(slots, progression)}


def load_bracket_slots() -> pd.DataFrame:
    create_default_bracket_files(False) if not BRACKET_SLOTS_PATH.exists() else None
    return pd.read_csv(BRACKET_SLOTS_PATH)


def load_round_progression() -> pd.DataFrame:
    create_default_bracket_files(False) if not ROUND_PROGRESSION_PATH.exists() else None
    return pd.read_csv(ROUND_PROGRESSION_PATH)


def build_round_of_32_from_group_results(group_standings_df: pd.DataFrame, bracket_slots_df: pd.DataFrame, third_place_assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for match_slot, slot_df in bracket_slots_df.groupby("match_slot", sort=False):
        row = {"stage": "Round of 32", "match_slot": match_slot, "team_a": None, "team_b": None, "unresolved": False}
        for _, slot in slot_df.iterrows():
            team = None
            if slot["qualifier_type"] in {"group_winner", "group_runner_up"}:
                group_rows = group_standings_df[group_standings_df["group"].astype(str).eq(str(slot["group"]))]
                match = group_rows[group_rows["group_rank"].eq(int(slot["placement"]))]
                if not match.empty:
                    team = match.iloc[0]["team"]
            elif slot["qualifier_type"] == "best_third_place":
                match = third_place_assignments[third_place_assignments["third_place_mapping_key"].eq(slot["third_place_mapping_key"])]
                if not match.empty:
                    team = match.iloc[0]["team"]
            if team is None or pd.isna(team):
                row["unresolved"] = True
            row[slot["team_slot"]] = team
        rows.append(row)
    return pd.DataFrame(rows)


def initialize_knockout_bracket(round_of_32_df: pd.DataFrame) -> pd.DataFrame:
    return round_of_32_df.copy()


def propagate_knockout_winner(knockout_state: pd.DataFrame, winner, from_match_slot: str, progression_df: pd.DataFrame) -> pd.DataFrame:
    match = progression_df[progression_df["from_match_slot"].eq(from_match_slot)]
    if match.empty:
        return knockout_state
    target = match.iloc[0]
    mask = knockout_state["match_slot"].eq(target["winner_feeds_to_match_slot"])
    if not mask.any():
        knockout_state = pd.concat([knockout_state, pd.DataFrame([{"stage": target["winner_feeds_to_stage"], "match_slot": target["winner_feeds_to_match_slot"], "team_a": None, "team_b": None, "unresolved": False}])], ignore_index=True)
        mask = knockout_state["match_slot"].eq(target["winner_feeds_to_match_slot"])
    knockout_state.loc[mask, target["winner_feeds_to_team_slot"]] = winner
    return knockout_state


def resolve_next_round_matches(bracket_state: pd.DataFrame, progression_df: pd.DataFrame) -> pd.DataFrame:
    return bracket_state


def bracket_is_complete(bracket_state: pd.DataFrame) -> bool:
    return bracket_state[["team_a", "team_b"]].notna().all().all()


def build_probability_lookup(predictions: pd.DataFrame) -> dict:
    lookup = {}
    for _, row in predictions[predictions.get("prediction_status", "") == "predicted"].iterrows():
        key = (str(row["team_a"]), str(row["team_b"]))
        lookup[key] = (row["prob_team_a_loss"], row["prob_draw"], row["prob_team_a_win"])
    return lookup


def get_dynamic_match_probabilities(team_a, team_b, probability_lookup: dict, team_ratings_df: pd.DataFrame | None = None, fallback_method: str = "elo", live_probability_lookup: dict | None = None) -> tuple[tuple[float, float, float], str]:
    key = (str(team_a), str(team_b))
    rev = (str(team_b), str(team_a))
    if live_probability_lookup:
        if key in live_probability_lookup:
            return tuple(float(x) for x in live_probability_lookup[key]), "live_model_exact"
        if rev in live_probability_lookup:
            loss, draw, win = live_probability_lookup[rev]
            return (float(win), float(draw), float(loss)), "live_model_reversed"
    if key in probability_lookup:
        return tuple(float(x) for x in probability_lookup[key]), "model_exact"
    if rev in probability_lookup:
        loss, draw, win = probability_lookup[rev]
        return (float(win), float(draw), float(loss)), "model_reversed"
    if fallback_method == "elo" and team_ratings_df is not None:
        if isinstance(team_ratings_df, dict):
            rating_map = team_ratings_df
        elif not team_ratings_df.empty:
            rating_value = team_ratings_df["elo_rating"].where(team_ratings_df["elo_rating"].notna(), team_ratings_df["fifa_points"]) if "elo_rating" in team_ratings_df.columns else team_ratings_df["fifa_points"]
            rating_map = dict(zip(team_ratings_df["team"], pd.to_numeric(rating_value, errors="coerce")))
        else:
            rating_map = {}
        ra = rating_map.get(team_a)
        rb = rating_map.get(team_b)
        if pd.notna(ra) and pd.notna(rb):
            expected = 1 / (1 + 10 ** ((rb - ra) / 400))
            draw = 0.26
            remaining = 0.74
            return (remaining * (1 - expected), draw, remaining * expected), "elo_fallback"
    return (0.35, 0.30, 0.35), "neutral_fallback"
