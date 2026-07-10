"""Full simulation pipeline."""

from __future__ import annotations

import pandas as pd

from src.simulation.aggregate_results import aggregate_simulation_results
from src.simulation.bracket_mapping import create_default_bracket_files
from src.simulation.bracket_reports import write_full_champion_simulation_summary
from src.simulation.bracket_validation import validate_bracket_mapping
from src.simulation.data_loader import load_simulation_inputs
from src.simulation.simulation_config import DEFAULT_N_SIMULATIONS, RANDOM_SEED, ensure_simulation_directories
from src.simulation.simulation_reports import write_monte_carlo_summary, write_simulation_limitations, write_team_advancement_summary
from src.simulation.simulation_validation import validate_simulation
from src.simulation.tournament_simulator import run_full_bracket_monte_carlo_simulations, run_monte_carlo_simulations
from src.simulation.tournament_structure import inspect_tournament_structure


def run_simulation_pipeline(n_simulations: int = DEFAULT_N_SIMULATIONS, seed: int = RANDOM_SEED, mode: str = "auto") -> dict:
    ensure_simulation_directories()
    inputs = load_simulation_inputs()
    structure = inspect_tournament_structure(inputs["predictions"])
    create_default_bracket_files(False)
    bracket_validation = validate_bracket_mapping()
    selected_mode = "full-bracket" if mode == "auto" and bracket_validation["status"] == "pass" else mode
    if selected_mode == "full-bracket":
        simulation_result = run_full_bracket_monte_carlo_simulations(n_simulations=n_simulations, seed=seed, inputs=inputs)
    else:
        selected_mode = "partial"
        simulation_result = run_monte_carlo_simulations(n_simulations=n_simulations, seed=seed, inputs=inputs)
    aggregate = aggregate_simulation_results(simulation_result)
    completion_rate = float(aggregate["completion_df"].iloc[0]["full_bracket_completed_rate"])
    full_possible = selected_mode == "full-bracket" and completion_rate >= 0.999
    post_validation = validate_simulation(inputs=inputs, aggregate=aggregate, n_simulations=n_simulations, full_champion_possible=full_possible)
    validate_bracket_mapping(aggregate["champion_df"], full_possible)
    unresolved = [sim["unresolved_count"] for sim in simulation_result["simulations"]]
    fallback = []
    for sim in simulation_result["simulations"]:
        if "used_fallback_count" in sim:
            fallback.append(sim["used_fallback_count"])
            continue
        source_counts = sim.get("probability_source_counts", {})
        fallback.append(source_counts.get("elo_fallback", 0) + source_counts.get("neutral_fallback", 0))
    summary = {
        "n_simulations": n_simulations,
        "full_champion_simulation_possible": full_possible,
        "avg_unresolved_count": sum(unresolved) / len(unresolved) if unresolved else 0,
        "avg_fallback_count": sum(fallback) / len(fallback) if fallback else 0,
    }
    reports = [
        inputs["report"],
        structure["report"],
        post_validation["report"],
        write_monte_carlo_summary(summary, aggregate),
        write_team_advancement_summary(aggregate["advancement_df"]),
        write_simulation_limitations(),
        write_full_champion_simulation_summary(aggregate),
    ]
    return {
        "status": "success" if selected_mode == "full-bracket" and full_possible else "partial_success",
        "mode": selected_mode,
        "n_simulations": n_simulations,
        "full_champion_simulation_possible": full_possible,
        "team_advancement_path": aggregate["team_advancement_path"],
        "champion_probabilities_path": aggregate["champion_probabilities_path"],
        "reports": reports,
    }
