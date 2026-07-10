"""Simulation reports."""

from __future__ import annotations

import pandas as pd

from src.simulation.simulation_config import SIMULATION_OUTPUT_DIR, SIMULATION_REPORT_DIR, ensure_simulation_directories


def write_monte_carlo_summary(summary: dict, aggregate: dict) -> str:
    ensure_simulation_directories()
    lines = [
        "# Monte Carlo Summary",
        "",
        f"- Simulations run: {summary['n_simulations']}",
        f"- Full champion simulation possible: {'yes' if summary.get('full_champion_simulation_possible') else 'no'}",
        f"- Average unresolved fixtures per simulation: {summary.get('avg_unresolved_count', 0):.2f}",
        f"- Average fallback probabilities used per simulation: {summary.get('avg_fallback_count', 0):.2f}",
        "",
        "Full champion simulation is not currently reliable because the knockout bracket mapping is incomplete or unresolved.",
    ]
    path = SIMULATION_REPORT_DIR / "monte_carlo_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_team_advancement_summary(advancement_df: pd.DataFrame) -> str:
    lines = ["# Team Advancement Summary", "", "## Top Round of 32 Probabilities", ""]
    if not advancement_df.empty:
        for _, row in advancement_df.sort_values("reach_round_of_32_prob", ascending=False).head(10).iterrows():
            lines.append(f"- {row['team']}: {row['reach_round_of_32_prob']:.3f}")
    path = SIMULATION_REPORT_DIR / "team_advancement_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_simulation_limitations() -> str:
    lines = [
        "# Simulation Limitations",
        "",
        "- Full champion simulation is not currently reliable because the knockout bracket mapping is incomplete or unresolved.",
        "- TBD/playoff placeholder teams are preserved and not treated as real teams.",
        "- Group-stage advancement uses the documented default assumption: top 2 teams per group advance.",
        "- Goal scores are not modeled; group standings use result-based points plus simple result-derived tiebreakers.",
        "- Completed results are fixed when present, but the current results file may be header-only.",
    ]
    path = SIMULATION_REPORT_DIR / "simulation_limitations.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_simulation_summary_printable(pipeline_result: dict) -> str:
    advancement_path = SIMULATION_OUTPUT_DIR / "team_advancement_probabilities.csv"
    champion_path = SIMULATION_OUTPUT_DIR / "champion_probabilities.csv"
    advancement = pd.read_csv(advancement_path) if advancement_path.exists() else pd.DataFrame()
    champion = pd.read_csv(champion_path) if champion_path.exists() else pd.DataFrame()
    simulation_count = pipeline_result.get("n_simulations")
    if (not simulation_count or str(simulation_count).startswith("see")) and not advancement.empty and "simulations" in advancement.columns:
        simulation_count = int(pd.to_numeric(advancement["simulations"], errors="coerce").dropna().max())
    lines = [
        "# Simulation Summary",
        "",
        f"- Simulations: {simulation_count or 'unknown'}",
        f"- Full champion simulation possible: {'yes' if pipeline_result.get('full_champion_simulation_possible') else 'no'}",
        f"- Team advancement path: `{advancement_path}`",
        f"- Champion probabilities path: `{champion_path}`",
        "",
        "## Top 10 Round of 32 Probabilities",
        "",
    ]
    if not advancement.empty:
        for _, row in advancement.sort_values("reach_round_of_32_prob", ascending=False).head(10).iterrows():
            lines.append(f"- {row['team']}: {row['reach_round_of_32_prob']:.3f}")
    lines.extend(["", "## Champion Probabilities", "", "Champion probabilities are blank/partial until bracket mapping is available."])
    path = SIMULATION_REPORT_DIR / "simulation_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[2:18]))
    return str(path)
