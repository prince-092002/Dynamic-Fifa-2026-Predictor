# Phase 5B Bracket Mapping Handoff

Saved: 2026-07-07  
Scope: FIFA 2026 fallback bracket mapping, full-bracket Monte Carlo simulation, and champion probability outputs. No secrets are included.

## What Changed

- Added explicit fallback bracket mapping files:
  - `data/bracket/fifa_2026_bracket_slots.csv`
  - `data/bracket/fifa_2026_round_progression.csv`
  - `data/bracket/fifa_2026_third_place_mapping.csv`
- Added bracket and third-place modules:
  - `src/simulation/bracket_config.py`
  - `src/simulation/bracket_mapping.py`
  - `src/simulation/third_place_rules.py`
  - `src/simulation/bracket_validation.py`
  - `src/simulation/bracket_reports.py`
- Added full-bracket simulation support while preserving partial mode:
  - `python main.py run-simulation --mode partial --n-simulations 10000`
  - `python main.py run-simulation --mode full-bracket --n-simulations 10000`
  - `python main.py run-simulation --mode auto --n-simulations 10000`
- Added CLI commands:
  - `inspect-bracket`
  - `validate-bracket`
  - `bracket-summary`
  - `champion-summary`
- Updated `README.md` with Phase 5B usage and fallback mapping caveats.

## Important Caveat

The bracket mapping is a transparent fallback template. It is not an official FIFA bracket or official third-place placement mapping. Replace it when FIFA publishes or confirms the final machine-readable bracket rules.

## Latest Verification

Commands run successfully:

```bash
python -m compileall src main.py
python main.py inspect-bracket
python main.py validate-bracket
python main.py run-simulation --mode partial --n-simulations 1000
python main.py run-simulation --mode full-bracket --n-simulations 1000
python main.py run-simulation --mode full-bracket --n-simulations 10000
python main.py validate-simulation
python main.py champion-summary
python main.py bracket-summary
```

Latest 10,000-run full-bracket result:

- Full bracket completion rate: `1.0000`
- Completed simulations: `10000 / 10000`
- Champion probability sum: `1.0`
- Champion probability rows: `42`
- Probability sources:
  - `model_exact`: `1118`
  - `model_reversed`: `685`
  - `elo_fallback`: `308197`
  - `neutral_fallback`: `0`

Top champion probabilities from latest run:

| Team | Champion count | Champion probability |
|---|---:|---:|
| Spain | 1264 | 0.1264 |
| Argentina | 1188 | 0.1188 |
| France | 1110 | 0.1110 |
| England | 832 | 0.0832 |
| Brazil | 708 | 0.0708 |

## Key Outputs

```text
outputs/simulations/team_advancement_probabilities.csv
outputs/simulations/champion_probabilities.csv
outputs/simulations/stage_probability_summary.csv
outputs/simulations/simulated_match_results_sample.csv
outputs/simulations/bracket_completion_summary.csv
outputs/simulations/probability_source_summary.csv
outputs/reports/simulation/bracket/bracket_source_report.md
outputs/reports/simulation/bracket/bracket_mapping_summary.md
outputs/reports/simulation/bracket/bracket_validation_report.md
outputs/reports/simulation/bracket/full_champion_simulation_summary.md
```

## Notes For Next Session

- Do not treat the fallback bracket as official.
- Do not remove TBD fixtures; they are preserved in predictions and partial simulation.
- Exact model probabilities only exist for currently known scheduled fixtures, so generated knockout matchups mostly use Elo fallback probabilities.
- `avg_unresolved_matches` in `bracket_completion_summary.csv` includes unresolved group-stage TBD fixtures from the source schedule; the full knockout bracket itself completed in every 10,000-run simulation.
- No dashboard was built.
