"""Reports for bracket mapping and champion simulation."""

from __future__ import annotations

import pandas as pd

from src.simulation.bracket_config import BRACKET_REPORT_DIR, ensure_bracket_directories


def write_bracket_source_report(source: str = "fallback_template") -> str:
    ensure_bracket_directories()
    lines = [
        "# Bracket Source Report",
        "",
        f"- Mapping source: {source}",
        "- Official bracket mapping found in local fixture data: no",
        "- Fallback mapping is used so full-bracket simulation can run.",
        "",
        "This fallback is not claimed to be the official FIFA bracket. Replace the CSV mapping files when official slot mapping is verified.",
    ]
    path = BRACKET_REPORT_DIR / "bracket_source_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_bracket_mapping_summary(slots: pd.DataFrame, progression: pd.DataFrame) -> str:
    lines = [
        "# Bracket Mapping Summary",
        "",
        f"- Round of 32 team slots: {len(slots)}",
        f"- Round progression rows: {len(progression)}",
        "- Mapping source: fallback_template",
        "",
        "The fallback mapping uses all 12 group winners, all 12 runners-up, and 8 best third-place slots.",
    ]
    path = BRACKET_REPORT_DIR / "bracket_mapping_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_full_champion_simulation_summary(aggregate: dict) -> str:
    champion = aggregate.get("champion_df", pd.DataFrame())
    completion = aggregate.get("completion_df", pd.DataFrame())
    sources = aggregate.get("source_df", pd.DataFrame())
    lines = ["# Full Champion Simulation Summary", ""]
    if not completion.empty:
        row = completion.iloc[0]
        lines.extend(
            [
                f"- Simulations: {row.get('simulations')}",
                f"- Full bracket completion rate: {row.get('full_bracket_completed_rate'):.4f}",
                f"- Average unresolved matches: {row.get('avg_unresolved_matches'):.4f}",
            ]
        )
    lines.extend(["", "## Top Champion Probabilities", ""])
    if not champion.empty:
        for _, row in champion.sort_values("champion_prob", ascending=False).head(10).iterrows():
            lines.append(f"- {row['team']}: {row['champion_prob']:.4f}")
    lines.extend(["", "## Probability Source Usage", ""])
    if not sources.empty:
        for _, row in sources.iterrows():
            lines.append(f"- {row['probability_source']}: {row['uses']}")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "Bracket mapping is fallback/template based, not verified official FIFA mapping.",
            "TBD/playoff placeholders are not treated as real teams.",
        ]
    )
    path = BRACKET_REPORT_DIR / "full_champion_simulation_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
