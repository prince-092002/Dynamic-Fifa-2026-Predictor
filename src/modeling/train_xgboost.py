"""Train XGBoost multiclass model."""

from __future__ import annotations

import joblib
import pandas as pd
from xgboost import XGBClassifier

from src.modeling.model_config import MODEL_DIR, MODELING_REPORT_DIR, RANDOM_SEED, ensure_modeling_directories


def train_xgboost_model(X_train, y_train, X_val=None, y_val=None, feature_columns: list[str] | None = None):
    ensure_modeling_directories()
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        n_estimators=500,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=RANDOM_SEED,
        n_jobs=2,
    )
    try:
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)] if X_val is not None else None, verbose=False)
    except TypeError:
        model.fit(X_train, y_train)
    path = MODEL_DIR / "xgboost_match_outcome_model.joblib"
    joblib.dump(model, path)
    feature_columns = feature_columns or list(X_train.columns)
    importances = pd.DataFrame({"feature": feature_columns, "importance": model.feature_importances_}).sort_values("importance", ascending=False)
    csv_path = MODELING_REPORT_DIR / "xgboost_feature_importance.csv"
    md_path = MODELING_REPORT_DIR / "xgboost_feature_importance.md"
    importances.to_csv(csv_path, index=False)
    lines = ["# XGBoost Feature Importance", "", "| Feature | Importance |", "|---|---:|"]
    for _, row in importances.head(50).iterrows():
        lines.append(f"| `{row['feature']}` | {row['importance']:.6f} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return model, str(path)
