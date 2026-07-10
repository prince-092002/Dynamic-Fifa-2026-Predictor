"""Central feature configuration and paths."""

from pathlib import Path

from src.config import DATA_DIR, OUTPUTS_DIR

FEATURE_DIR = DATA_DIR / "features"
FEATURE_INTERMEDIATE_DIR = FEATURE_DIR / "intermediate"
FEATURE_FINAL_DIR = FEATURE_DIR / "final"
FEATURE_REPORT_DIR = OUTPUTS_DIR / "reports" / "features"

MATCHES_FEATURE_CLEAN_PATH = FEATURE_INTERMEDIATE_DIR / "matches_master_feature_clean.csv"
FIXTURES_FEATURE_CLEAN_PATH = FEATURE_INTERMEDIATE_DIR / "fixtures_2026_feature_clean.csv"
TEAM_HISTORY_PATH = FEATURE_INTERMEDIATE_DIR / "team_match_history.csv"

TRAINING_DATASET_PATH = FEATURE_FINAL_DIR / "match_training_dataset.csv"
FIXTURE_FEATURES_PATH = FEATURE_FINAL_DIR / "fixture_2026_features.csv"

ROLLING_WINDOWS = [3, 5, 10]
MIN_HISTORY_REQUIRED = 3
DEFAULT_NEUTRAL_VALUE = False

TARGET_COLUMNS = [
    "team_a_goals",
    "team_b_goals",
    "team_a_win",
    "draw",
    "team_b_win",
    "match_result",
]

FEATURE_GROUPS = {
    "rating": "Current FIFA/Elo rating features for fixtures",
    "elo": "Leakage-safe chronological Elo features",
    "form": "Recent team form features",
    "goal": "Attacking and defensive goal performance",
    "head_to_head": "Previous meetings between the two teams",
    "tournament": "Tournament and stage context",
    "schedule": "Rest and congestion features",
}

MODEL_FEATURE_COLUMNS = [
    "team_a_pre_match_elo",
    "team_b_pre_match_elo",
    "elo_difference",
    "elo_expected_score_team_a",
    "form_points_last_5_diff",
    "win_rate_last_5_diff",
    "loss_rate_last_5_diff",
    "goals_for_avg_last_5_diff",
    "goals_against_avg_last_5_diff",
    "goal_diff_avg_last_5_diff",
    "clean_sheet_rate_last_5_diff",
    "h2h_matches_last_10",
    "h2h_team_a_win_rate_last_10",
    "h2h_goal_diff_team_a_last_10",
    "is_world_cup_match",
    "is_friendly",
    "is_qualifier",
    "is_knockout",
    "is_group_stage",
    "is_neutral",
    "stage_encoded",
    "tournament_importance_score",
    "team_a_days_since_last_match",
    "team_b_days_since_last_match",
    "rest_days_diff",
    "team_a_matches_last_30_days",
    "team_b_matches_last_30_days",
    "match_congestion_diff",
]

FIXTURE_RATING_FEATURE_COLUMNS = [
    "team_a_elo_rating",
    "team_b_elo_rating",
    "elo_rating_diff",
    "team_a_elo_rank",
    "team_b_elo_rank",
    "elo_rank_diff",
    "team_a_fifa_rank",
    "team_b_fifa_rank",
    "fifa_rank_diff",
    "team_a_fifa_points",
    "team_b_fifa_points",
    "fifa_points_diff",
]


def ensure_feature_directories() -> None:
    """Create feature output folders."""
    for path in [FEATURE_DIR, FEATURE_INTERMEDIATE_DIR, FEATURE_FINAL_DIR, FEATURE_REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)
