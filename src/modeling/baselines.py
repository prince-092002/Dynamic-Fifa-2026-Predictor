"""Baseline probability models."""

from __future__ import annotations

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.modeling.evaluate import CLASSES, align_proba


class FixedProbabilityModel:
    def __init__(self, probabilities):
        self.probabilities = np.asarray(probabilities, dtype=float)

    def predict_proba(self, X):
        return np.tile(self.probabilities, (len(X), 1))

    def predict(self, X):
        return np.full(len(X), int(CLASSES[np.argmax(self.probabilities)]))


def train_majority_baseline(y_train):
    counts = np.bincount(y_train, minlength=3)
    probs = np.zeros(3)
    probs[np.argmax(counts)] = 1.0
    return FixedProbabilityModel(probs)


def train_frequency_baseline(y_train):
    counts = np.bincount(y_train, minlength=3).astype(float)
    return FixedProbabilityModel(counts / counts.sum())


def train_elo_logistic_baseline(train_df, feature_name: str = "elo_difference"):
    if feature_name not in train_df.columns:
        return None, f"{feature_name} not available"
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(train_df[[feature_name]], train_df["match_result"])
    return model, ""


def predict_model(model, X):
    proba = model.predict_proba(X)
    classes = getattr(model, "classes_", CLASSES)
    if hasattr(model, "named_steps"):
        classes = model.named_steps["model"].classes_
    proba = align_proba(proba, classes)
    return np.argmax(proba, axis=1), proba
