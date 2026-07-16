# Live Knockout Prediction Report

- Generated: 2026-07-16T00:15:25+00:00
- Known remaining knockout matchups: 1
- Predicted by live model: 1
- Failed (missing features): 0
- Knockout matches skipped because they are completed: 30
- Knockout matches skipped because participants are TBD: 0
- Model used: xgboost

## Feature Completeness

- Spain vs Argentina (Final): complete (0 missing feature values)

## Live Model Predictions

| Stage | Match | P(team A win) | P(draw) | P(team A loss) | P(A advances) | Source | Status |
|---|---|---:|---:|---:|---:|---|---|
| Final | Spain vs Argentina | 0.4079 | 0.2232 | 0.3689 | 0.5195 | live_model | predicted |

## Probability Source Usage (simulated matches)

| Source | Previous run | Latest run |
|---|---:|---:|
| live_model_exact | 10000 | 10000 |

- Elo/neutral fallback share before: 0.00%
- Elo/neutral fallback share after: 0.00%
- Fallback reduction: +0.00%

## Remaining Limitations

- Semifinal/final matchups stay on Elo fallback inside each simulation until their participants are known in the real bracket.
- Live model predictions reuse pre-tournament feature definitions; they are regenerated per round, not per simulation branch.
- Elo fallback remains as backup and is always labeled as fallback, never as a model prediction.