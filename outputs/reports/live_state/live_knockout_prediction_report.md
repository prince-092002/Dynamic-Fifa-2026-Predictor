# Live Knockout Prediction Report

- Generated: 2026-07-14T21:07:08+00:00
- Known remaining knockout matchups: 1
- Predicted by live model: 1
- Failed (missing features): 0
- Knockout matches skipped because they are completed: 29
- Knockout matches skipped because participants are TBD: 1
- Model used: xgboost

## Feature Completeness

- England vs Argentina (Semifinal): complete (0 missing feature values)

## Live Model Predictions

| Stage | Match | P(team A win) | P(draw) | P(team A loss) | P(A advances) | Source | Status |
|---|---|---:|---:|---:|---:|---|---|
| Semifinal | England vs Argentina | 0.2869 | 0.2129 | 0.5002 | 0.3933 | live_model | predicted |

## Probability Source Usage (simulated matches)

| Source | Previous run | Latest run |
|---|---:|---:|
| completed_result | 10000 | 10000 |
| elo_fallback | 29510 | 10000 |
| live_model_exact | 30000 | 10000 |
| model_reversed | 490 | 0 |

- Elo/neutral fallback share before: 42.16%
- Elo/neutral fallback share after: 33.33%
- Fallback reduction: +8.82%

## Remaining Limitations

- Semifinal/final matchups stay on Elo fallback inside each simulation until their participants are known in the real bracket.
- Live model predictions reuse pre-tournament feature definitions; they are regenerated per round, not per simulation branch.
- Elo fallback remains as backup and is always labeled as fallback, never as a model prediction.