# Final-Stage Probability Consistency Audit

## Decision

When exactly one unresolved championship Final remains with two known teams and a
valid live-model prediction, the direct two-way final advancement probabilities are
the canonical championship probabilities. Monte Carlo winner frequencies remain in
the output as diagnostics, not as the public title probability.

## Before

| Display | Spain | Argentina | Definition |
|---|---:|---:|---|
| Champion forecast | 52.23% | 47.77% | 10,000 Monte Carlo final-winner samples |
| Final prediction | 51.9471408% | 48.0528592% | Direct XGBoost advancement probability |

Both came from run `2026-07-15T215633Z-91cbff83`, seed 42. The difference was
sampling variation, not stale data, team inversion, rounding, fallback use, or a
different model artifact.

## Provenance

| UI value | Public data | Field | Generator |
|---|---|---|---|
| Champion probability | `public_data/champion_forecast.json` | `entries[].champion_probability` | `aggregate_live_finalist_results()` |
| Homepage leader | `public_data/latest_overview.json` | `top_champion_probability` | `_build_overview()` from live forecast summary |
| Final card | `public_data/matchup_predictions.json` | `team_a_advance_probability`, `team_b_advance_probability` | `predict_live_knockout_matchups()` |
| Bracket final | `public_data/knockout_bracket.json` | `team_a_advance_probability`, `team_b_advance_probability` | `_build_bracket()` from live matchup prediction |

The XGBoost class order is team-A loss, draw, team-A win. Knockout advancement is:

`team_a = win + 0.5 * draw`

`team_b = loss + 0.5 * draw`

For the current Final, raw probabilities are 0.3689239731 loss, 0.2232092387 draw,
and 0.4078667881 win for team A. This yields 0.5194714075 and 0.4805285925.

## Controlled Sampling

| Seed | Simulations | Spain estimate | Difference from direct |
|---:|---:|---:|---:|
| 42 | 10,000 | 52.2300% | +0.2829 points |
| 1 | 10,000 | 51.6500% | -0.2971 points |
| 7 | 10,000 | 51.9100% | -0.0371 points |
| 21 | 10,000 | 51.5100% | -0.4371 points |
| 99 | 10,000 | 51.5300% | -0.4171 points |
| 42 | 100,000 | 51.7600% | -0.1871 points |
| 42 | 1,000,000 | 51.9709% | +0.0238 points |

The sample converges toward the direct final probability. Re-sampling the only
remaining Bernoulli decision adds noise without adding bracket information.

## Corrected Rerun

- Refresh: `refresh-2026-07-16T001411Z-2e7673`
- Forecast run: `2026-07-16T001427Z-9f49d25b`
- Provider: `football_data_org`, fresh API
- Phase: final
- Completed matches: 102
- Final: Argentina vs Spain
- Model: XGBoost
- Simulations: 10,000
- Seed: 42
- Elo fallback: not used
- Canonical Spain championship probability: 51.9471408%
- Canonical Argentina championship probability: 48.0528592%
- Diagnostic Monte Carlo frequencies: 52.23% and 47.77%
- Final-stage invariant maximum difference: 0.000000000000

## Integrity

The selected model artifact and all six pre-existing Prediction History snapshot
files remained byte-identical. A new genuine snapshot was appended at
`data/prediction_history/snapshots/20260716T001525Z__final__102_completed.json`.
