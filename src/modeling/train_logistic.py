"""Train multinomial Logistic Regression."""

from __future__ import annotations

import joblib
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.modeling.model_config import MODEL_DIR, RANDOM_SEED, ensure_modeling_directories


def train_logistic_regression(X_train, y_train):
    ensure_modeling_directories()
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=RANDOM_SEED)),
        ]
    )
    model.fit(X_train, y_train)
    path = MODEL_DIR / "logistic_regression_model.joblib"
    joblib.dump(model, path)
    return model, str(path)
