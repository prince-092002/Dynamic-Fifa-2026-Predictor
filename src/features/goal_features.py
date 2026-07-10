"""Rolling attacking and defensive features."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR, ROLLING_WINDOWS


def build_rolling_goal_features(team_history_df: pd.DataFrame, windows=ROLLING_WINDOWS) -> pd.DataFrame:
    history = team_history_df.copy().sort_values(["team", "date", "match_id"])
    grouped = history.groupby("team", group_keys=False)
    for window in windows:
        for source, agg, name in [
            ("goals_for", "mean", f"goals_for_avg_last_{window}"),
            ("goals_against", "mean", f"goals_against_avg_last_{window}"),
            ("goal_diff", "mean", f"goal_diff_avg_last_{window}"),
        ]:
            shifted = grouped[source].shift(1)
            history[name] = shifted.groupby(history["team"]).rolling(window, min_periods=1).mean().reset_index(level=0, drop=True)
    shifted_gf = grouped["goals_for"].shift(1)
    history["goals_for_sum_last_5"] = shifted_gf.groupby(history["team"]).rolling(5, min_periods=1).sum().reset_index(level=0, drop=True)
    shifted_cs = grouped["clean_sheet_flag"].shift(1)
    history["clean_sheet_rate_last_5"] = shifted_cs.groupby(history["team"]).rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
    return history


def _join_goal_side(base: pd.DataFrame, goal_df: pd.DataFrame, team_col: str, prefix: str) -> pd.DataFrame:
    cols = [c for c in goal_df.columns if c.startswith(("goals_", "goal_diff_", "clean_sheet_"))]
    lookup = goal_df[["match_id", "team", *cols]].rename(columns={"team": team_col, **{c: f"{prefix}_{c}" for c in cols}})
    return base.merge(lookup, on=["match_id", team_col], how="left")


def join_goal_features_to_matches(matches_df: pd.DataFrame, goal_df: pd.DataFrame) -> pd.DataFrame:
    output = matches_df[["match_id", "team_a", "team_b"]].copy()
    output = _join_goal_side(output, goal_df, "team_a", "team_a")
    output = _join_goal_side(output, goal_df, "team_b", "team_b")
    output["goals_for_avg_last_5_diff"] = output["team_a_goals_for_avg_last_5"] - output["team_b_goals_for_avg_last_5"]
    output["goals_against_avg_last_5_diff"] = output["team_a_goals_against_avg_last_5"] - output["team_b_goals_against_avg_last_5"]
    output["goal_diff_avg_last_5_diff"] = output["team_a_goal_diff_avg_last_5"] - output["team_b_goal_diff_avg_last_5"]
    output["clean_sheet_rate_last_5_diff"] = output["team_a_clean_sheet_rate_last_5"] - output["team_b_clean_sheet_rate_last_5"]
    output.to_csv(FEATURE_INTERMEDIATE_DIR / "historical_goal_features.csv", index=False)
    return output


def build_current_fixture_goal_features(fixtures_df: pd.DataFrame, team_history_df: pd.DataFrame) -> pd.DataFrame:
    goals = build_rolling_goal_features(team_history_df)
    latest = goals.sort_values(["team", "date"]).groupby("team").tail(1)
    rows = fixtures_df[["match_id", "team_a", "team_b"]].copy()
    goal_cols = [c for c in latest.columns if c.startswith(("goals_", "goal_diff_", "clean_sheet_"))]
    for side in ["team_a", "team_b"]:
        lookup = latest[["team", *goal_cols]].rename(columns={"team": side, **{c: f"{side}_{c}" for c in goal_cols}})
        rows = rows.merge(lookup, on=side, how="left")
    rows["goals_for_avg_last_5_diff"] = rows["team_a_goals_for_avg_last_5"] - rows["team_b_goals_for_avg_last_5"]
    rows["goals_against_avg_last_5_diff"] = rows["team_a_goals_against_avg_last_5"] - rows["team_b_goals_against_avg_last_5"]
    rows["goal_diff_avg_last_5_diff"] = rows["team_a_goal_diff_avg_last_5"] - rows["team_b_goal_diff_avg_last_5"]
    rows["clean_sheet_rate_last_5_diff"] = rows["team_a_clean_sheet_rate_last_5"] - rows["team_b_clean_sheet_rate_last_5"]
    rows.to_csv(FEATURE_INTERMEDIATE_DIR / "fixture_goal_features.csv", index=False)
    return rows
