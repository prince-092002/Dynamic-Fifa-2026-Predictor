"""Best third-place qualification rules."""

from __future__ import annotations

import pandas as pd

from src.simulation.bracket_config import BRACKET_REPORT_DIR, THIRD_PLACE_MAPPING_PATH, ensure_bracket_directories


def rank_third_place_teams(group_standings_df: pd.DataFrame) -> pd.DataFrame:
    thirds = group_standings_df[group_standings_df["group_rank"].eq(3)].copy()
    if thirds.empty:
        return thirds
    thirds = thirds.sort_values(["points", "goal_difference", "goals_for"], ascending=[False, False, False]).reset_index(drop=True)
    thirds["rank_among_thirds"] = thirds.index + 1
    thirds["qualifies_as_best_third"] = thirds["rank_among_thirds"] <= 8
    return thirds


def select_best_third_place_teams(group_standings_df: pd.DataFrame) -> pd.DataFrame:
    return rank_third_place_teams(group_standings_df).query("qualifies_as_best_third == True").copy()


def assign_best_third_place_slots(best_third_df: pd.DataFrame, mapping_config: pd.DataFrame | None = None, write_report: bool = True) -> pd.DataFrame:
    ensure_bracket_directories()
    mapping_config = mapping_config if mapping_config is not None else pd.read_csv(THIRD_PLACE_MAPPING_PATH)
    assigned = best_third_df.sort_values("rank_among_thirds").head(8).copy()
    assigned["third_place_mapping_key"] = [f"TP_SLOT_{i}" for i in range(1, len(assigned) + 1)]
    assigned["mapping_source"] = "fallback_rank_order"
    if write_report:
        lines = [
            "# Third-Place Assignment Report",
            "",
            "- Mapping source: fallback_rank_order",
            "- This is not official FIFA third-place placement mapping.",
            "",
            "| Slot | Team | Group | Rank among thirds |",
            "|---|---|---|---:|",
        ]
        for _, row in assigned.iterrows():
            lines.append(f"| {row['third_place_mapping_key']} | {row['team']} | {row['group']} | {row['rank_among_thirds']} |")
        path = BRACKET_REPORT_DIR / "third_place_assignment_report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
    return assigned
