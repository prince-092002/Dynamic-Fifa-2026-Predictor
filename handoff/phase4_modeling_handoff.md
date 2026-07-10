# Phase 4 Modeling Handoff

Project: Dynamic FIFA 2026 Tournament Outcome Predictor  
Date: 2026-07-06  
Scope completed: baseline and machine-learning modeling pipeline. No Monte Carlo simulation, automated bracket simulation, Streamlit dashboard, or tournament simulator was built.

## Commands Added

```bash
python main.py modeling-data-summary
python main.py train-models
python main.py evaluate-models
python main.py predict-fixtures
python main.py modeling-summary
```

## New Package

```text
src/modeling/
```

Key modules:

- `model_config.py`
- `data_loader.py`
- `feature_selection.py`
- `splits.py`
- `baselines.py`
- `train_logistic.py`
- `train_xgboost.py`
- `evaluate.py`
- `calibration.py`
- `predict_fixtures.py`
- `model_registry.py`
- `model_reports.py`
- `model_pipeline.py`

## Modeling Setup

- Target: `match_result`
- Target classes:
  - `0 = team_a_loss`
  - `1 = draw`
  - `2 = team_a_win`
- Primary split: chronological, not random.
- Split proportions:
  - 70% train
  - 15% validation
  - 15% test
- Model selection rule: lowest validation log loss.
- Selected feature columns are saved to:
  - `outputs/reports/modeling/selected_feature_columns.txt`
  - `outputs/reports/modeling/selected_feature_columns.csv`

## Models Trained

- Majority class baseline
- Historical frequency baseline
- Elo-only Logistic Regression baseline
- Multinomial Logistic Regression
- XGBoost multiclass classifier

## Selected Model

```text
xgboost
```

Selected by lowest validation log loss.

Validation metrics:

```text
accuracy:    0.5824
macro_f1:    0.4301
log_loss:    0.8978
brier_score: 0.5293
```

Test metrics:

```text
accuracy:    0.6075
macro_f1:    0.4511
log_loss:    0.8607
brier_score: 0.5056
```

## Outputs

Models:

```text
outputs/models/logistic_regression_model.joblib
outputs/models/xgboost_match_outcome_model.joblib
outputs/models/selected_model.joblib
outputs/models/model_registry.json
```

Predictions:

```text
outputs/predictions/fixture_2026_match_predictions.csv
```

Reports:

```text
outputs/reports/modeling/modeling_data_summary.md
outputs/reports/modeling/split_report.md
outputs/reports/modeling/model_metrics.csv
outputs/reports/modeling/model_comparison.md
outputs/reports/modeling/calibration_report.md
outputs/reports/modeling/xgboost_feature_importance.csv
outputs/reports/modeling/xgboost_feature_importance.md
outputs/reports/modeling/fixture_prediction_summary.md
outputs/reports/modeling/modeling_phase_summary.md
```

## Fixture Prediction State

Latest prediction file contains:

```text
Total fixtures:       104
Predicted fixtures:    51
Not predictable rows:  53
```

TBD/unpredictable fixture rows are preserved and marked:

```text
prediction_status = not_predictable_tbd_or_missing_features
```

Predictable rows receive:

```text
prob_team_a_loss
prob_draw
prob_team_a_win
predicted_result
predicted_result_label
confidence
```

## Important Limitations

- FIFA 2026 results are still header-only, so the model has no completed 2026 tournament matches yet.
- Team stats and player stats are header-only, so they are not part of the model.
- TBD fixtures are preserved but not predicted yet.
- Draw recall is very low in the selected model. Review before using predictions for high-stakes decisions.
- Predictions are probabilistic, not guarantees.

## Commands Verified

```bash
python -m compileall src main.py scripts
python main.py modeling-data-summary
python main.py train-models
python main.py evaluate-models
python main.py predict-fixtures
python main.py modeling-summary
```

## Next Step

Review `outputs/reports/modeling/model_comparison.md` and `outputs/predictions/fixture_2026_match_predictions.csv`. The next phase can build Monte Carlo tournament simulation using these match probabilities, but that was intentionally not built in Phase 4.
