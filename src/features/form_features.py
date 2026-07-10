"""Recent form features built from prior matches only."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR, ROLLING_WINDOWS, ensure_feature_directories


def calculate_team_match_history(matches_df: pd.DataFrame) -> pd.DataFrame:
    ensure_feature_directories()
    rows = []
    for _, row in matches_df.iterrows():
        a_goals = pd.to_numeric(row.get("team_a_goals"), errors="coerce")
        b_goals = pd.to_numeric(row.get("team_b_goals"), errors="coerce")
        if pd.isna(a_goals) or pd.isna(b_goals):
            continue
        for side in ["a", "b"]:
            is_a = side == "a"
            gf = a_goals if is_a else b_goals
            ga = b_goals if is_a else a_goals
            result_points = 3 if gf > ga else 1 if gf == ga else 0
            rows.append(
                {
                    "match_id": row.get("match_id"),
                    "date": row.get("date"),
                    "team": row.get("team_a" if is_a else "team_b"),
                    "opponent": row.get("team_b" if is_a else "team_a"),
                    "goals_for": gf,
                    "goals_against": ga,
                    "goal_diff": gf - ga,
                    "result_points": result_points,
                    "win_flag": int(result_points == 3),
                    "draw_flag": int(result_points == 1),
                    "loss_flag": int(result_points == 0),
                    "clean_sheet_flag": int(ga == 0),
                    "tournament": row.get("tournament"),
                    "neutral": row.get("neutral"),
                    "source": row.get("source"),
                }
            )
    history = pd.DataFrame(rows)
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history = history.sort_values(["team", "date", "match_id"]).reset_index(drop=True)
    history.to_csv(FEATURE_INTERMEDIATE_DIR / "team_match_history.csv", index=False)
    return history


def build_rolling_form_features(team_history_df: pd.DataFrame, windows=ROLLING_WINDOWS) -> pd.DataFrame:
    history = team_history_df.copy().sort_values(["team", "date", "match_id"])
    grouped = history.groupby("team", group_keys=False)
    for window in windows:
        shifted_points = grouped["result_points"].shift(1)
        shifted_win = grouped["win_flag"].shift(1)
        history[f"form_points_last_{window}"] = shifted_points.groupby(history["team"]).rolling(window, min_periods=1).sum().reset_index(level=0, drop=True)
        history[f"win_rate_last_{window}"] = shifted_win.groupby(history["team"]).rolling(window, min_periods=1).mean().reset_index(level=0, drop=True)
    for column, source in [("draw_rate_last_5", "draw_flag"), ("loss_rate_last_5", "loss_flag")]:
        shifted = grouped[source].shift(1)
        history[column] = shifted.groupby(history["team"]).rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
    return history


def _join_team_features(matches_df: pd.DataFrame, features_df: pd.DataFrame, prefix: str, team_col: str) -> pd.DataFrame:
    feature_cols = [c for c in features_df.columns if c.startswith(("form_points_", "win_rate_", "draw_rate_", "loss_rate_"))]
    lookup = features_df[["match_id", "team", *feature_cols]].copy()
    lookup = lookup.rename(columns={c: f"{prefix}_{c}" for c in feature_cols})
    return matches_df.merge(lookup, left_on=["match_id", team_col], right_on=["match_id", "team"], how="left").drop(columns=["team"], errors="ignore")


def join_form_features_to_matches(matches_df: pd.DataFrame, form_df: pd.DataFrame) -> pd.DataFrame:
    output = matches_df[["match_id"]].copy()
    output = _join_team_features(matches_df[["match_id", "team_a"]], form_df, "team_a", "team_a")
    output = output.merge(_join_team_features(matches_df[["match_id", "team_b"]], form_df, "team_b", "team_b"), on="match_id", how="left")
    output["form_points_last_5_diff"] = output["team_a_form_points_last_5"] - output["team_b_form_points_last_5"]
    output["win_rate_last_5_diff"] = output["team_a_win_rate_last_5"] - output["team_b_win_rate_last_5"]
    output["loss_rate_last_5_diff"] = output["team_a_loss_rate_last_5"] - output["team_b_loss_rate_last_5"]
    output.to_csv(FEATURE_INTERMEDIATE_DIR / "historical_form_features.csv", index=False)
    return output


def build_current_fixture_form_features(fixtures_df: pd.DataFrame, team_history_df: pd.DataFrame) -> pd.DataFrame:
    form = build_rolling_form_features(team_history_df)
    latest = form.sort_values(["team", "date"]).groupby("team").tail(1)
    rows = fixtures_df[["match_id", "team_a", "team_b"]].copy()
    for side in ["team_a", "team_b"]:
        side_latest = latest.rename(columns={"team": side})
        cols = [c for c in side_latest.columns if c.startswith(("form_points_", "win_rate_", "draw_rate_", "loss_rate_"))]
        rows = rows.merge(side_latest[[side, *cols]], on=side, how="left", suffixes=("", f"_{side}"))
        rows = rows.rename(columns={c: f"{side}_{c}" for c in cols if c in rows.columns})
    rows["form_points_last_5_diff"] = rows["team_a_form_points_last_5"] - rows["team_b_form_points_last_5"]
    rows["win_rate_last_5_diff"] = rows["team_a_win_rate_last_5"] - rows["team_b_win_rate_last_5"]
    rows["loss_rate_last_5_diff"] = rows["team_a_loss_rate_last_5"] - rows["team_b_loss_rate_last_5"]
    rows.to_csv(FEATURE_INTERMEDIATE_DIR / "fixture_form_features.csv", index=False)
    return rows
