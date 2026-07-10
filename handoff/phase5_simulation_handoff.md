# Phase 5 Monte Carlo Simulation Handoff

Project: Dynamic FIFA 2026 Tournament Outcome Predictor  
Date: 2026-07-06  
Scope completed: partial Monte Carlo tournament simulation pipeline using Phase 4 fixture probabilities. No Streamlit dashboard, automated bracket simulator, or bracket-mapping engine was built.

## Commands Added

```bash
python main.py simulation-input-summary
python main.py run-simulation --n-simulations 1000
python main.py run-simulation --n-simulations 10000
python main.py validate-simulation
python main.py simulation-summary
```

## New Package

```text
src/simulation/
```

Key modules:

- `simulation_config.py`
- `data_loader.py`
- `tournament_structure.py`
- `match_sampler.py`
- `group_stage.py`
- `knockout_stage.py`
- `tournament_simulator.py`
- `aggregate_results.py`
- `simulation_validation.py`
- `simulation_reports.py`
- `simulation_pipeline.py`

## Inputs Used

```text
outputs/predictions/fixture_2026_match_predictions.csv
data/features/final/fixture_2026_features.csv
data/processed/fixtures_2026.csv
data/processed/results_2026.csv
```

Latest prediction state:

```text
Total fixtures:       104
Predicted fixtures:    51
Not predictable rows:  53
```

## Simulation Behavior

- Group-stage matches allow draws.
- Knockout matches convert draw probability into advancement probability:
  - `team_a_advancement = prob_team_a_win + 0.5 * prob_draw`
  - `team_b_advancement = prob_team_a_loss + 0.5 * prob_draw`
- TBD/playoff placeholders are preserved and not treated as real teams.
- Completed results are loaded and preserved if present; current results may be header-only.
- Group-stage advancement uses the documented default assumption:
  - top 2 teams per group advance.
- Full champion simulation is disabled/marked unreliable because group-to-knockout bracket mapping is incomplete or unresolved in the current fixture data.

## Outputs

```text
outputs/simulations/team_advancement_probabilities.csv
outputs/simulations/champion_probabilities.csv
outputs/simulations/stage_probability_summary.csv
outputs/simulations/simulated_match_results_sample.csv
```

Reports:

```text
outputs/reports/simulation/simulation_input_summary.md
outputs/reports/simulation/tournament_structure_report.md
outputs/reports/simulation/simulation_validation_report.md
outputs/reports/simulation/monte_carlo_summary.md
outputs/reports/simulation/team_advancement_summary.md
outputs/reports/simulation/simulation_limitations.md
outputs/reports/simulation/simulation_summary.md
```

## Latest Run

`python main.py run-simulation --n-simulations 10000` completed successfully.

Latest summary:

```text
Simulations run: 10000
Full champion simulation possible: no
Average unresolved fixtures per simulation: 53.00
Average fallback probabilities used per simulation: 0.00
Simulation validation status: pass
```

Top Round of 32 probabilities from latest summary:

```text
Argentina      0.977
Spain          0.956
England        0.943
Mexico         0.942
Portugal       0.933
United States  0.919
Belgium        0.918
France         0.906
Germany        0.900
```

## Important Limitations

- Full champion simulation is not currently reliable because the knockout bracket mapping is incomplete or unresolved.
- Champion probabilities are intentionally blank/partial in `champion_probabilities.csv`.
- The current simulator estimates partial advancement from group-stage simulations, not a complete bracket path.
- Goal scores are not modeled; group standings use result-based points plus simple result-derived tiebreakers.
- TBD fixtures and playoff placeholders are preserved but not predicted/simulated as real teams.

## Commands Verified

```bash
python -m compileall src main.py scripts
python main.py simulation-input-summary
python main.py run-simulation --n-simulations 1000
python main.py validate-simulation
python main.py simulation-summary
python main.py run-simulation --n-simulations 10000
python main.py validate-simulation
python main.py simulation-summary
```

## Next Step

Before building a dashboard, decide whether to add explicit FIFA 2026 bracket mapping and best-third-place advancement rules. That would allow reliable champion simulation instead of partial advancement estimates.
