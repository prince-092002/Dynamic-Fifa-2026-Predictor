"""Leakage-safe Elo feature engineering."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR, ensure_feature_directories


def initialize_elo_ratings(teams, current_team_ratings: pd.DataFrame | None = None) -> dict[str, float]:
    ratings = {str(team): 1500.0 for team in teams if pd.notna(team)}
    if current_team_ratings is not None and not current_team_ratings.empty:
        rating_col = "elo_rating" if "elo_rating" in current_team_ratings.columns else "fifa_points"
        for _, row in current_team_ratings.iterrows():
            team = row.get("team")
            rating = pd.to_numeric(row.get(rating_col), errors="coerce")
            if pd.notna(team) and pd.notna(rating):
                ratings[str(team)] = float(rating)
    return ratings


def expected_score(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def actual_score(team_a_goals, team_b_goals) -> float | None:
    a = pd.to_numeric(team_a_goals, errors="coerce")
    b = pd.to_numeric(team_b_goals, errors="coerce")
    if pd.isna(a) or pd.isna(b):
        return None
    if a > b:
        return 1.0
    if a == b:
        return 0.5
    return 0.0


def update_elo(elo_a: float, elo_b: float, score_a: float, k_factor: float = 30) -> tuple[float, float]:
    expected_a = expected_score(elo_a, elo_b)
    new_a = elo_a + k_factor * (score_a - expected_a)
    new_b = elo_b + k_factor * ((1 - score_a) - (1 - expected_a))
    return new_a, new_b


def build_chronological_elo_features(matches_df: pd.DataFrame) -> pd.DataFrame:
    ensure_feature_directories()
    matches = matches_df.copy()
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
    matches = matches.sort_values(["date", "match_id"], na_position="last").reset_index(drop=True)
    teams = pd.concat([matches["team_a"], matches["team_b"]]).dropna().unique()
    ratings = initialize_elo_ratings(teams)
    rows = []
    for _, row in matches.iterrows():
        team_a = str(row.get("team_a"))
        team_b = str(row.get("team_b"))
        elo_a = ratings.get(team_a, 1500.0)
        elo_b = ratings.get(team_b, 1500.0)
        score_a = actual_score(row.get("team_a_goals"), row.get("team_b_goals"))
        rows.append(
            {
                "match_id": row.get("match_id"),
                "team_a_pre_match_elo": elo_a,
                "team_b_pre_match_elo": elo_b,
                "elo_difference": elo_a - elo_b,
                "elo_expected_score_team_a": expected_score(elo_a, elo_b),
            }
        )
        if score_a is not None:
            ratings[team_a], ratings[team_b] = update_elo(elo_a, elo_b, score_a)
    output = pd.DataFrame(rows)
    output.to_csv(FEATURE_INTERMEDIATE_DIR / "historical_elo_features.csv", index=False)
    return output


def build_current_fixture_elo_features(fixtures_df: pd.DataFrame, team_ratings_df: pd.DataFrame) -> pd.DataFrame:
    ensure_feature_directories()
    fixtures = fixtures_df.copy()
    ratings = team_ratings_df.copy()
    if ratings.empty:
        ratings = pd.DataFrame(columns=["team", "elo_rating", "fifa_points"])
    rating_value = ratings["elo_rating"].where(ratings.get("elo_rating").notna(), ratings.get("fifa_points")) if "elo_rating" in ratings else ratings.get("fifa_points")
    rating_map = dict(zip(ratings.get("team", []), pd.to_numeric(rating_value, errors="coerce")))
    rows = []
    for _, row in fixtures.iterrows():
        a = rating_map.get(row.get("team_a"))
        b = rating_map.get(row.get("team_b"))
        rows.append(
            {
                "match_id": row.get("match_id"),
                "team_a_current_elo": a,
                "team_b_current_elo": b,
                "elo_difference": a - b if pd.notna(a) and pd.notna(b) else pd.NA,
                "elo_expected_score_team_a": expected_score(a, b) if pd.notna(a) and pd.notna(b) else pd.NA,
                "team_a_rating_missing": pd.isna(a),
                "team_b_rating_missing": pd.isna(b),
            }
        )
    output = pd.DataFrame(rows)
    output.to_csv(FEATURE_INTERMEDIATE_DIR / "fixture_elo_features.csv", index=False)
    return output
