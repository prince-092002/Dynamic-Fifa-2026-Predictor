"""Head-to-head features built only from previous meetings."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR


def _pair(a, b) -> tuple[str, str]:
    return tuple(sorted([str(a), str(b)]))


def _h2h_before(history: pd.DataFrame, date, team_a, team_b) -> dict:
    pair = _pair(team_a, team_b)
    prior = history[(history["date"] < date) & (history["pair"].apply(lambda value: value == pair))].tail(10)
    if prior.empty:
        return {
            "h2h_matches_last_10": 0,
            "h2h_team_a_wins_last_10": 0,
            "h2h_team_b_wins_last_10": 0,
            "h2h_draws_last_10": 0,
            "h2h_team_a_win_rate_last_10": pd.NA,
            "h2h_goal_diff_team_a_last_10": pd.NA,
        }
    a_wins = ((prior["winner"] == team_a)).sum()
    b_wins = ((prior["winner"] == team_b)).sum()
    draws = (prior["winner"] == "Draw").sum()
    gd = prior.apply(lambda row: row["team_a_goals"] - row["team_b_goals"] if row["team_a"] == team_a else row["team_b_goals"] - row["team_a_goals"], axis=1)
    return {
        "h2h_matches_last_10": len(prior),
        "h2h_team_a_wins_last_10": int(a_wins),
        "h2h_team_b_wins_last_10": int(b_wins),
        "h2h_draws_last_10": int(draws),
        "h2h_team_a_win_rate_last_10": a_wins / len(prior),
        "h2h_goal_diff_team_a_last_10": gd.mean(),
    }


def build_head_to_head_features(matches_df: pd.DataFrame, target_df: pd.DataFrame, output_name: str) -> pd.DataFrame:
    history = matches_df.copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history["pair"] = history.apply(lambda row: _pair(row.get("team_a"), row.get("team_b")), axis=1)
    history = history.sort_values("date")
    target = target_df.copy()
    target["date"] = pd.to_datetime(target["date"], errors="coerce")
    if len(target) > 5000:
        pair_history: dict[tuple[str, str], list[dict]] = {}
        rows = []
        for _, row in history.iterrows():
            pair = row["pair"]
            prior = pair_history.get(pair, [])[-10:]
            if not prior:
                values = {
                    "h2h_matches_last_10": 0,
                    "h2h_team_a_wins_last_10": 0,
                    "h2h_team_b_wins_last_10": 0,
                    "h2h_draws_last_10": 0,
                    "h2h_team_a_win_rate_last_10": pd.NA,
                    "h2h_goal_diff_team_a_last_10": pd.NA,
                }
            else:
                team_a = row.get("team_a")
                team_b = row.get("team_b")
                a_wins = sum(1 for item in prior if item.get("winner") == team_a)
                b_wins = sum(1 for item in prior if item.get("winner") == team_b)
                draws = sum(1 for item in prior if item.get("winner") == "Draw")
                goal_diffs = []
                for item in prior:
                    a_goals = pd.to_numeric(item.get("team_a_goals"), errors="coerce")
                    b_goals = pd.to_numeric(item.get("team_b_goals"), errors="coerce")
                    if pd.isna(a_goals) or pd.isna(b_goals):
                        continue
                    goal_diffs.append(a_goals - b_goals if item.get("team_a") == team_a else b_goals - a_goals)
                values = {
                    "h2h_matches_last_10": len(prior),
                    "h2h_team_a_wins_last_10": a_wins,
                    "h2h_team_b_wins_last_10": b_wins,
                    "h2h_draws_last_10": draws,
                    "h2h_team_a_win_rate_last_10": a_wins / len(prior),
                    "h2h_goal_diff_team_a_last_10": sum(goal_diffs) / len(goal_diffs) if goal_diffs else pd.NA,
                }
            values["match_id"] = row.get("match_id")
            rows.append(values)
            pair_history.setdefault(pair, []).append(
                {
                    "team_a": row.get("team_a"),
                    "team_b": row.get("team_b"),
                    "team_a_goals": row.get("team_a_goals"),
                    "team_b_goals": row.get("team_b_goals"),
                    "winner": row.get("winner"),
                }
            )
        output = pd.DataFrame(rows)
        output.to_csv(FEATURE_INTERMEDIATE_DIR / output_name, index=False)
        return output
    rows = []
    for _, row in target.iterrows():
        values = _h2h_before(history, row.get("date"), row.get("team_a"), row.get("team_b"))
        values["match_id"] = row.get("match_id")
        rows.append(values)
    output = pd.DataFrame(rows)
    output.to_csv(FEATURE_INTERMEDIATE_DIR / output_name, index=False)
    return output
