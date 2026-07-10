"""Rest and schedule congestion features."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR


def _team_history_dates(matches_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in matches_df.iterrows():
        for team_col in ["team_a", "team_b"]:
            rows.append({"match_id": row.get("match_id"), "date": row.get("date"), "team": row.get(team_col)})
    history = pd.DataFrame(rows)
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    return history.dropna(subset=["date", "team"]).sort_values(["team", "date"])


def build_schedule_features(matches_df: pd.DataFrame, target_df: pd.DataFrame, output_name: str) -> pd.DataFrame:
    history = _team_history_dates(matches_df)
    target = target_df.copy()
    target["date"] = pd.to_datetime(target["date"], errors="coerce")
    if len(target) > 5000:
        team_dates: dict[str, list[pd.Timestamp]] = {}
        rows = []
        target = target.sort_values(["date", "match_id"], na_position="last")
        for _, row in target.iterrows():
            values = {"match_id": row.get("match_id")}
            match_date = row.get("date")
            for side in ["team_a", "team_b"]:
                team = row.get(side)
                prior_dates = team_dates.get(team, [])
                if prior_dates and pd.notna(match_date):
                    values[f"{side}_days_since_last_match"] = (match_date - prior_dates[-1]).days
                    cutoff = match_date - pd.Timedelta(days=30)
                    count = 0
                    for prior_date in reversed(prior_dates):
                        if prior_date < cutoff:
                            break
                        count += 1
                    values[f"{side}_matches_last_30_days"] = count
                else:
                    values[f"{side}_days_since_last_match"] = pd.NA
                    values[f"{side}_matches_last_30_days"] = 0
            values["rest_days_diff"] = values["team_a_days_since_last_match"] - values["team_b_days_since_last_match"] if pd.notna(values["team_a_days_since_last_match"]) and pd.notna(values["team_b_days_since_last_match"]) else pd.NA
            values["match_congestion_diff"] = values["team_a_matches_last_30_days"] - values["team_b_matches_last_30_days"]
            rows.append(values)
            if pd.notna(match_date):
                for side in ["team_a", "team_b"]:
                    team_dates.setdefault(row.get(side), []).append(match_date)
        output = pd.DataFrame(rows)
        output.to_csv(FEATURE_INTERMEDIATE_DIR / output_name, index=False)
        return output
    rows = []
    for _, row in target.iterrows():
        values = {"match_id": row.get("match_id")}
        for side in ["team_a", "team_b"]:
            team_prior = history[(history["team"] == row.get(side)) & (history["date"] < row.get("date"))]
            last_date = team_prior["date"].max() if not team_prior.empty else pd.NaT
            values[f"{side}_days_since_last_match"] = (row.get("date") - last_date).days if pd.notna(last_date) and pd.notna(row.get("date")) else pd.NA
            values[f"{side}_matches_last_30_days"] = int((team_prior["date"] >= row.get("date") - pd.Timedelta(days=30)).sum()) if pd.notna(row.get("date")) else 0
        values["rest_days_diff"] = values["team_a_days_since_last_match"] - values["team_b_days_since_last_match"] if pd.notna(values["team_a_days_since_last_match"]) and pd.notna(values["team_b_days_since_last_match"]) else pd.NA
        values["match_congestion_diff"] = values["team_a_matches_last_30_days"] - values["team_b_matches_last_30_days"]
        rows.append(values)
    output = pd.DataFrame(rows)
    output.to_csv(FEATURE_INTERMEDIATE_DIR / output_name, index=False)
    return output
