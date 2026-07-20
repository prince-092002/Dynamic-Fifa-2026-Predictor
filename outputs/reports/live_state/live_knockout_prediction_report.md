# Live Knockout Prediction Report

- Generated: 2026-07-20T06:05:48+00:00
- Known remaining knockout matchups: 0
- Predicted by live model: 0
- Failed (missing features): 0
- Knockout matches skipped because they are completed: 31
- Knockout matches skipped because participants are TBD: 0
- Model used: unknown

## Feature Completeness

No live knockout feature rows were generated.

## Live Model Predictions

| Stage | Match | P(team A win) | P(draw) | P(team A loss) | P(A advances) | Source | Status |
|---|---|---:|---:|---:|---:|---|---|
| - | No predictions generated | - | - | - | - | - | - |

## Probability Source Usage (simulated matches)

| Source | Previous run | Latest run |
|---|---:|---:|
| completed_result | 10000 | 10000 |

- Elo/neutral fallback share before: 0.00%
- Elo/neutral fallback share after: 0.00%
- Fallback reduction: +0.00%

## Remaining Limitations

- Semifinal/final matchups stay on Elo fallback inside each simulation until their participants are known in the real bracket.
- Live model predictions reuse pre-tournament feature definitions; they are regenerated per round, not per simulation branch.
- Elo fallback remains as backup and is always labeled as fallback, never as a model prediction.