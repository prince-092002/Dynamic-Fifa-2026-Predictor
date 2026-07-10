# Model Comparison

- Selected by lowest validation log loss: `xgboost`
- Probability metrics, especially log loss and Brier score, should matter more than accuracy.

| Model | Split | Accuracy | Macro F1 | Log loss | Brier score |
|---|---|---:|---:|---:|---:|
| majority_class_baseline | validation | 0.4802 | 0.2163 | 18.7342 | 1.0395 |
| majority_class_baseline | test | 0.4795 | 0.2161 | 18.7607 | 1.0410 |
| historical_frequency_baseline | validation | 0.4802 | 0.2163 | 1.0505 | 0.6333 |
| historical_frequency_baseline | test | 0.4795 | 0.2161 | 1.0498 | 0.6330 |
| elo_logistic_baseline | validation | 0.5515 | 0.4978 | 0.9469 | 0.5608 |
| elo_logistic_baseline | test | 0.5850 | 0.5180 | 0.8958 | 0.5281 |
| logistic_regression | validation | 0.5475 | 0.5148 | 0.9325 | 0.5524 |
| logistic_regression | test | 0.5752 | 0.5273 | 0.8872 | 0.5241 |
| xgboost | validation | 0.5824 | 0.4301 | 0.8978 | 0.5293 |
| xgboost | test | 0.6075 | 0.4511 | 0.8607 | 0.5056 |