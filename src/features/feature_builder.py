"""Orchestrate feature engineering into final datasets."""

from __future__ import annotations

import pandas as pd

from src.config import PROCESSED_DIR
from src.features.data_quality import run_feature_data_quality_checks
from src.features.elo_features import build_chronological_elo_features, build_current_fixture_elo_features
from src.features.feature_config import (
    FEATURE_INTERMEDIATE_DIR,
    FIXTURE_FEATURES_PATH,
    FIXTURES_FEATURE_CLEAN_PATH,
    MATCHES_FEATURE_CLEAN_PATH,
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMNS,
    TRAINING_DATASET_PATH,
    ensure_feature_directories,
)
from src.features.form_features import (
    build_current_fixture_form_features,
    build_rolling_form_features,
    calculate_team_match_history,
    join_form_features_to_matches,
)
from src.features.goal_features import build_current_fixture_goal_features, build_rolling_goal_features, join_goal_features_to_matches
from src.features.head_to_head_features import build_head_to_head_features
from src.features.rating_features import build_fixture_rating_features
from src.features.schedule_features import build_schedule_features
from src.features.tournament_features import build_tournament_features


def _read(path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _merge_features(base: pd.DataFrame, feature_tables: list[pd.DataFrame]) -> pd.DataFrame:
    output = base.copy()
    for table in feature_tables:
        if table.empty or "match_id" not in table.columns:
            continue
        drop_cols = [c for c in ["team_a", "team_b", "date"] if c in table.columns]
        table = table.drop(columns=drop_cols, errors="ignore")
        output = output.merge(table, on="match_id", how="left")
    return output


def _add_targets(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    output["team_a_goals"] = pd.to_numeric(output["team_a_goals"], errors="coerce")
    output["team_b_goals"] = pd.to_numeric(output["team_b_goals"], errors="coerce")
    output = output.dropna(subset=["team_a_goals", "team_b_goals"]).copy()
    output["team_a_win"] = output["team_a_goals"] > output["team_b_goals"]
    output["draw"] = output["team_a_goals"] == output["team_b_goals"]
    output["team_b_win"] = output["team_a_goals"] < output["team_b_goals"]
    output["match_result"] = output.apply(lambda row: 2 if row["team_a_win"] else 1 if row["draw"] else 0, axis=1)
    return output


def build_historical_training_features() -> pd.DataFrame:
    ensure_feature_directories()
    matches = _read(MATCHES_FEATURE_CLEAN_PATH)
    if matches.empty:
        matches = _read(PROCESSED_DIR / "matches_master.csv")
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
    target_base = _add_targets(matches)
    team_history = calculate_team_match_history(target_base)
    form = build_rolling_form_features(team_history)
    goals = build_rolling_goal_features(team_history)
    feature_tables = [
        build_chronological_elo_features(target_base),
        join_form_features_to_matches(target_base, form),
        join_goal_features_to_matches(target_base, goals),
        build_head_to_head_features(target_base, target_base, "historical_h2h_features.csv"),
        build_tournament_features(target_base, "historical_tournament_features.csv"),
        build_schedule_features(target_base, target_base, "historical_schedule_features.csv"),
    ]
    identifiers = ["match_id", "date", "team_a", "team_b", "tournament", "stage", "source"]
    base = target_base[[c for c in identifiers + TARGET_COLUMNS if c in target_base.columns]].copy()
    final = _merge_features(base, feature_tables)
    for column in MODEL_FEATURE_COLUMNS:
        if column not in final.columns:
            final[column] = pd.NA
    final.to_csv(TRAINING_DATASET_PATH, index=False)
    return final


def build_2026_fixture_features() -> pd.DataFrame:
    ensure_feature_directories()
    fixtures = _read(FIXTURES_FEATURE_CLEAN_PATH)
    if fixtures.empty:
        fixtures = _read(PROCESSED_DIR / "fixtures_2026.csv")
    fixtures["date"] = pd.to_datetime(fixtures["date"], errors="coerce")
    if "fixture_has_tbd_team" not in fixtures.columns:
        fixtures["team_a_is_tbd"] = fixtures["team_a"].isna() | fixtures["team_a"].astype(str).str.startswith("TBD")
        fixtures["team_b_is_tbd"] = fixtures["team_b"].isna() | fixtures["team_b"].astype(str).str.startswith("TBD")
        fixtures["fixture_has_tbd_team"] = fixtures["team_a_is_tbd"] | fixtures["team_b_is_tbd"]
    matches = _read(MATCHES_FEATURE_CLEAN_PATH)
    if matches.empty:
        matches = _read(PROCESSED_DIR / "matches_master.csv")
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
    team_history = calculate_team_match_history(_add_targets(matches))
    ratings = _read(PROCESSED_DIR / "team_ratings.csv")
    feature_tables = [
        build_current_fixture_elo_features(fixtures, ratings),
        build_fixture_rating_features(fixtures, ratings),
        build_current_fixture_form_features(fixtures, team_history),
        build_current_fixture_goal_features(fixtures, team_history),
        build_head_to_head_features(matches, fixtures, "fixture_h2h_features.csv"),
        build_tournament_features(fixtures.assign(tournament="FIFA World Cup"), "fixture_tournament_features.csv"),
        build_schedule_features(matches, fixtures, "fixture_schedule_features.csv"),
    ]
    identifiers = ["match_id", "date", "team_a", "team_b", "stage", "group", "venue", "status", "team_a_is_tbd", "team_b_is_tbd", "fixture_has_tbd_team"]
    base = fixtures[[c for c in identifiers if c in fixtures.columns]].copy()
    final = _merge_features(base, feature_tables)
    critical = ["team_a_rating_missing", "team_b_rating_missing", "form_points_last_5_diff"]
    final["is_predictable_now"] = ~final["fixture_has_tbd_team"].fillna(True)
    for column in critical:
        if column in final.columns:
            if column.endswith("_missing"):
                final["is_predictable_now"] &= ~final[column].fillna(True)
            else:
                final["is_predictable_now"] &= final[column].notna()
    final.to_csv(FIXTURE_FEATURES_PATH, index=False)
    return final


def build_all_features() -> dict:
    ensure_feature_directories()
    quality = run_feature_data_quality_checks()
    training = build_historical_training_features()
    fixtures = build_2026_fixture_features()
    return {
        "quality": quality,
        "training_rows": len(training),
        "fixture_rows": len(fixtures),
        "training_output": str(TRAINING_DATASET_PATH),
        "fixture_output": str(FIXTURE_FEATURES_PATH),
    }
