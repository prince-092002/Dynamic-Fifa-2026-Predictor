# Modeling Phase Summary

- Best model selected: xgboost
- Prediction output path: `C:\Users\abelp\Desktop\Fifa Project\outputs\predictions\fixture_2026_match_predictions.csv`
- Fixture predictions rows: 104
- Predicted fixture rows: 51
- Validation metrics: {'model': 'xgboost', 'split': 'validation', 'accuracy': 0.5824146275880613, 'macro_f1': 0.4301344951518131, 'weighted_f1': 0.5055627730322673, 'log_loss': 0.897823061908177, 'brier_score': 0.529260769097607, 'precision_class_0': 0.5452528837622005, 'precision_class_1': 0.3333333333333333, 'precision_class_2': 0.601364522417154, 'recall_class_0': 0.5783529411764706, 'recall_class_1': 0.0103388856978747, 'recall_class_2': 0.8636618141097424}
- Test metrics: {'model': 'xgboost', 'split': 'test', 'accuracy': 0.6074741228659766, 'macro_f1': 0.4510675043406742, 'weighted_f1': 0.5298400600830204, 'log_loss': 0.8607220399132883, 'brier_score': 0.5055903524650359, 'precision_class_0': 0.5894596988485385, 'precision_class_1': 0.4565217391304347, 'precision_class_2': 0.6167478091528724, 'recall_class_0': 0.6136468418626095, 'recall_class_1': 0.0123311802701115, 'recall_class_2': 0.887860947574993}

## Limitations

- FIFA 2026 results are not fully loaded while `results_2026.csv` is header-only.
- Team stats/player stats are not included while their processed files are header-only.
- Fixtures with TBD teams are preserved but not predicted yet.
- Predictions are probabilistic, not guarantees.

## Next Recommended Step

Review model comparison and fixture predictions before starting Monte Carlo simulation in a separate phase.