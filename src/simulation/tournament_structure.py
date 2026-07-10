"""Inspect and classify FIFA 2026 tournament fixtures."""

from __future__ import annotations

import pandas as pd

from src.simulation.simulation_config import SIMULATION_REPORT_DIR, ensure_simulation_directories, normalize_stage


def is_tbd_team(team_name) -> bool:
    if pd.isna(team_name):
        return True
    text = str(team_name).strip().lower()
    if not text:
        return True
    markers = ["tbd", "unknown", "winner ", "runner", "playoff", "play-off", "placeholder", "team_a", "team_b"]
    return any(marker in text for marker in markers)


def fixture_is_simulatable_now(row) -> bool:
    if is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")):
        return False
    probs = [row.get("prob_team_a_loss"), row.get("prob_draw"), row.get("prob_team_a_win")]
    return all(pd.notna(pd.to_numeric(prob, errors="coerce")) for prob in probs)


def identify_group_stage_matches(fixtures_df: pd.DataFrame) -> pd.DataFrame:
    stages = fixtures_df.get("stage", pd.Series("", index=fixtures_df.index)).apply(normalize_stage)
    return fixtures_df[stages.eq("Group Stage")].copy()


def identify_knockout_matches(fixtures_df: pd.DataFrame) -> pd.DataFrame:
    stages = fixtures_df.get("stage", pd.Series("", index=fixtures_df.index)).apply(normalize_stage)
    return fixtures_df[~stages.eq("Group Stage")].copy()


def inspect_tournament_structure(fixtures_df: pd.DataFrame) -> dict:
    ensure_simulation_directories()
    data = fixtures_df.copy()
    data["normalized_stage"] = data.get("stage", pd.Series("", index=data.index)).apply(normalize_stage)
    known_teams = sorted(
        {
            str(team)
            for team in pd.concat([data.get("team_a", pd.Series(dtype=object)), data.get("team_b", pd.Series(dtype=object))]).dropna()
            if not is_tbd_team(team)
        }
    )
    tbd_rows = data[data.apply(lambda row: is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")), axis=1)]
    stage_counts = data["normalized_stage"].value_counts(dropna=False)
    group_counts = data.get("group", pd.Series(dtype=object)).value_counts(dropna=False)
    lines = ["# Tournament Structure Report", "", "## Matches by Stage", ""]
    for stage, count in stage_counts.items():
        lines.append(f"- {stage}: {count}")
    lines.extend(["", "## Groups", ""])
    for group, count in group_counts.items():
        lines.append(f"- {group}: {count}")
    lines.extend(
        [
            "",
            f"- Known teams detected: {len(known_teams)}",
            f"- Fixture rows with TBD/placeholders: {len(tbd_rows)}",
            "",
            "Bracket mapping from group advancers to knockout slots is not fully encoded in the current fixture data.",
        ]
    )
    path = SIMULATION_REPORT_DIR / "tournament_structure_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "stage_counts": stage_counts.to_dict(),
        "known_team_count": len(known_teams),
        "tbd_fixture_rows": len(tbd_rows),
        "full_bracket_mapping_available": False,
        "report": str(path),
    }
