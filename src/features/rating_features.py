"""Current team rating features for upcoming fixtures."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR, FIXTURE_RATING_FEATURE_COLUMNS


def build_fixture_rating_features(fixtures_df: pd.DataFrame, team_ratings_df: pd.DataFrame) -> pd.DataFrame:
    ratings = team_ratings_df.copy()
    output = fixtures_df[["match_id", "team_a", "team_b"]].copy()
    keep = ["team", "elo_rating", "elo_rank", "fifa_rank", "fifa_points"]
    for column in keep:
        if column not in ratings.columns:
            ratings[column] = pd.NA
    for side in ["team_a", "team_b"]:
        lookup = ratings[keep].rename(columns={"team": side, **{c: f"{side}_{c}" for c in keep if c != "team"}})
        output = output.merge(lookup, on=side, how="left")
    output["elo_rating_diff"] = output["team_a_elo_rating"] - output["team_b_elo_rating"]
    output["elo_rank_diff"] = output["team_b_elo_rank"] - output["team_a_elo_rank"]
    output["fifa_rank_diff"] = output["team_b_fifa_rank"] - output["team_a_fifa_rank"]
    output["fifa_points_diff"] = output["team_a_fifa_points"] - output["team_b_fifa_points"]
    for column in FIXTURE_RATING_FEATURE_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    output[["match_id", *FIXTURE_RATING_FEATURE_COLUMNS]].to_csv(FEATURE_INTERMEDIATE_DIR / "fixture_rating_features.csv", index=False)
    return output[["match_id", *FIXTURE_RATING_FEATURE_COLUMNS]]
