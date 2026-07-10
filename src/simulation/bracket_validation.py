"""Validate explicit bracket mapping files and champion outputs."""

from __future__ import annotations

import pandas as pd

from src.simulation.bracket_config import BRACKET_REPORT_DIR, BRACKET_SLOTS_PATH, ROUND_PROGRESSION_PATH, THIRD_PLACE_MAPPING_PATH, ensure_bracket_directories
from src.simulation.bracket_mapping import create_default_bracket_files, load_bracket_slots, load_round_progression


def _row(check: str, status: str, message: str, rows_affected: int = 0) -> dict:
    return {"check": check, "status": status, "message": message, "rows_affected": rows_affected}


def validate_bracket_mapping(champion_df: pd.DataFrame | None = None, full_bracket_possible: bool = True) -> dict:
    ensure_bracket_directories()
    create_default_bracket_files(False)
    rows = []
    rows.append(_row("bracket_slot_file_exists", "pass" if BRACKET_SLOTS_PATH.exists() else "fail", str(BRACKET_SLOTS_PATH)))
    rows.append(_row("round_progression_file_exists", "pass" if ROUND_PROGRESSION_PATH.exists() else "fail", str(ROUND_PROGRESSION_PATH)))
    rows.append(_row("third_place_mapping_file_exists", "pass" if THIRD_PLACE_MAPPING_PATH.exists() else "fail", str(THIRD_PLACE_MAPPING_PATH)))
    slots = load_bracket_slots()
    progression = load_round_progression()
    rows.append(_row("round_of_32_team_slots", "pass" if len(slots) == 32 else "fail", f"{len(slots)} team slots", len(slots)))
    rows.append(_row("round_of_32_matches", "pass" if slots["match_slot"].nunique() == 16 else "fail", f"{slots['match_slot'].nunique()} matches", slots["match_slot"].nunique()))
    expected_progression = {"R16": 8, "QF": 4, "SF": 2, "FINAL": 1}
    for prefix, count in expected_progression.items():
        actual = progression[progression["winner_feeds_to_match_slot"].astype(str).str.startswith(prefix)]["winner_feeds_to_match_slot"].nunique()
        rows.append(_row(f"{prefix}_match_count", "pass" if actual == count else "fail", f"{actual} matches", actual))
    final_feeds = progression[progression["winner_feeds_to_stage"].eq("Final")]
    rows.append(_row("progression_paths_to_final", "pass" if len(final_feeds) == 2 else "fail", f"{len(final_feeds)} semifinal winners feed final", len(final_feeds)))
    third_slots = slots[slots["qualifier_type"].eq("best_third_place")]
    rows.append(_row("best_third_place_slots_assigned", "pass" if len(third_slots) == 8 else "fail", f"{len(third_slots)} third-place slots", len(third_slots)))
    if champion_df is not None and not champion_df.empty and full_bracket_possible:
        total = pd.to_numeric(champion_df["champion_prob"], errors="coerce").sum()
        rows.append(_row("champion_probabilities_sum", "pass" if abs(total - 1) <= 0.02 else "fail", f"sum={total:.4f}"))
    df = pd.DataFrame(rows)
    csv_path = BRACKET_REPORT_DIR / "bracket_validation_report.csv"
    md_path = BRACKET_REPORT_DIR / "bracket_validation_report.md"
    df.to_csv(csv_path, index=False)
    lines = ["# Bracket Validation Report", "", "| Check | Status | Message | Rows affected |", "|---|---|---|---:|"]
    for _, row in df.iterrows():
        lines.append(f"| {row['check']} | {row['status']} | {row['message']} | {row['rows_affected']} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "fail" if (df["status"] == "fail").any() else "pass", "report": str(md_path), "csv": str(csv_path)}
