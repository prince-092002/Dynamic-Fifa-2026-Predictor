# Live Knockout Prediction Report

- Generated: 2026-07-10T06:52:42+00:00
- Known remaining knockout matchups: 3
- Predicted by live model: 3
- Failed (missing features): 0
- Knockout matches skipped because they are completed: 25
- Knockout matches skipped because participants are TBD: 3
- Model used: xgboost

## Feature Completeness

- Spain vs Belgium (Quarterfinal): complete (0 missing feature values)
- Norway vs England (Quarterfinal): complete (0 missing feature values)
- Argentina vs Switzerland (Quarterfinal): complete (0 missing feature values)

## Live Model Predictions

| Stage | Match | P(team A win) | P(draw) | P(team A loss) | P(A advances) | Source | Status |
|---|---|---:|---:|---:|---:|---|---|
| Quarterfinal | Spain vs Belgium | 0.6427 | 0.1946 | 0.1627 | 0.7400 | live_model | predicted |
| Quarterfinal | Norway vs England | 0.2344 | 0.2550 | 0.5106 | 0.3619 | live_model | predicted |
| Quarterfinal | Argentina vs Switzerland | 0.6834 | 0.1708 | 0.1458 | 0.7688 | live_model | predicted |

## Probability Source Usage (simulated matches)

| Source | Previous run | Latest run |
|---|---:|---:|
| completed_result | 10000 | 10000 |
| elo_fallback | 29510 | 29510 |
| live_model_exact | 30000 | 30000 |
| model_reversed | 490 | 490 |

- Elo/neutral fallback share before: 42.16%
- Elo/neutral fallback share after: 42.16%
- Fallback reduction: +0.00%

## Remaining Limitations

- Semifinal/final matchups stay on Elo fallback inside each simulation until their participants are known in the real bracket.
- Live model predictions reuse pre-tournament feature definitions; they are regenerated per round, not per simulation branch.
- Elo fallback remains as backup and is always labeled as fallback, never as a model prediction.