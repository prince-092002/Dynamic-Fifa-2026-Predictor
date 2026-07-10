"""Fallback bracket configuration for FIFA 2026 simulation.

The official FIFA tiebreaker and bracket rules may include additional criteria.
This project currently approximates late tiebreakers and discloses fallback mapping
when verified official bracket mapping is not available in the local data.
"""

from src.config import DATA_DIR, OUTPUTS_DIR

BRACKET_DATA_DIR = DATA_DIR / "bracket"
BRACKET_REPORT_DIR = OUTPUTS_DIR / "reports" / "simulation" / "bracket"

BRACKET_SLOTS_PATH = BRACKET_DATA_DIR / "fifa_2026_bracket_slots.csv"
ROUND_PROGRESSION_PATH = BRACKET_DATA_DIR / "fifa_2026_round_progression.csv"
THIRD_PLACE_MAPPING_PATH = BRACKET_DATA_DIR / "fifa_2026_third_place_mapping.csv"

GROUPS = list("ABCDEFGHIJKL")
STAGES = ["Group Stage", "Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final"]

QUALIFICATION_RULES = {
    "group_winners": 12,
    "group_runners_up": 12,
    "best_third_place": 8,
    "round_of_32_teams": 32,
}

GROUP_TIEBREAKERS = ["points", "goal_difference", "goals_for", "fair_play_placeholder", "random_tiebreaker"]
THIRD_PLACE_TIEBREAKERS = ["points", "goal_difference", "goals_for", "random_tiebreaker"]


def ensure_bracket_directories() -> None:
    BRACKET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRACKET_REPORT_DIR.mkdir(parents=True, exist_ok=True)
