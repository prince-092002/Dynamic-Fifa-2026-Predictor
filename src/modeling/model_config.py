"""Modeling configuration and paths."""

from src.config import DATA_DIR, OUTPUTS_DIR
from src.features.feature_config import FIXTURE_FEATURES_PATH, MODEL_FEATURE_COLUMNS, TRAINING_DATASET_PATH

MODELING_DIR = DATA_DIR / "modeling"
MODEL_DIR = OUTPUTS_DIR / "models"
PREDICTION_DIR = OUTPUTS_DIR / "predictions"
MODELING_REPORT_DIR = OUTPUTS_DIR / "reports" / "modeling"

TARGET_COLUMN = "match_result"
RANDOM_SEED = 42
TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
TEST_FRACTION = 0.15

EXCLUDE_COLUMNS = {
    "match_id",
    "date",
    "team_a",
    "team_b",
    "team_a_goals",
    "team_b_goals",
    "team_a_win",
    "draw",
    "team_b_win",
    "match_result",
    "winner",
    "source",
    "status",
    "venue",
    "city",
    "country",
    "stage",
    "group",
    "tournament",
    "predicted_result",
}

LEAKAGE_TERMS = ["goal", "winner", "result", "post_match", "future"]


def ensure_modeling_directories() -> None:
    for path in [MODELING_DIR, MODEL_DIR, PREDICTION_DIR, MODELING_REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)
