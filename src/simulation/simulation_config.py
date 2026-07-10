"""Simulation configuration and stage normalization."""

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.feature_config import FIXTURE_FEATURES_PATH

DEFAULT_N_SIMULATIONS = 10_000
RANDOM_SEED = 42

PREDICTION_FILE_PATH = OUTPUTS_DIR / "predictions" / "fixture_2026_match_predictions.csv"
PROCESSED_FIXTURES_PATH = PROCESSED_DIR / "fixtures_2026.csv"
PROCESSED_RESULTS_PATH = PROCESSED_DIR / "results_2026.csv"
SIMULATION_OUTPUT_DIR = OUTPUTS_DIR / "simulations"
SIMULATION_REPORT_DIR = OUTPUTS_DIR / "reports" / "simulation"

STAGE_ORDER = ["Group Stage", "Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final"]
STAGE_SCORE = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

GROUP_ADVANCER_RULES = {
    "top_n_per_group": 2,
    "best_third_place_count": 0,
    "note": "Default assumption for partial simulation: top 2 teams per group advance. Best third-place mapping is not inferred.",
}


def ensure_simulation_directories() -> None:
    for path in [SIMULATION_OUTPUT_DIR, SIMULATION_REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_stage(stage) -> str:
    text = str(stage or "").strip().lower()
    if text in {"group", "group stage", "groups"}:
        return "Group Stage"
    if text in {"r32", "round of 32", "last 32"}:
        return "Round of 32"
    if text in {"round of 16", "last 16", "r16"}:
        return "Round of 16"
    if text in {"quarter-finals", "quarterfinals", "quarterfinal", "quarter finals"}:
        return "Quarterfinal"
    if text in {"semi-finals", "semifinals", "semifinal", "semi finals"}:
        return "Semifinal"
    if text in {"third-place", "third place", "third place playoff", "third-place playoff"}:
        return "Third Place Playoff"
    if text == "final":
        return "Final"
    return str(stage or "Unknown")
