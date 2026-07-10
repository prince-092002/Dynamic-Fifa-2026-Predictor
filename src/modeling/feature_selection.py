"""Safe feature selection for modeling."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import MODEL_FEATURE_COLUMNS
from src.modeling.model_config import EXCLUDE_COLUMNS, MODELING_REPORT_DIR, TARGET_COLUMN, ensure_modeling_directories


def get_safe_feature_columns(df: pd.DataFrame) -> list[str]:
    candidates = [column for column in MODEL_FEATURE_COLUMNS if column in df.columns]
    safe = []
    for column in candidates:
        if column in EXCLUDE_COLUMNS:
            continue
        if not (pd.api.types.is_numeric_dtype(df[column]) or pd.api.types.is_bool_dtype(df[column])):
            continue
        if df[column].isna().mean() > 0.60:
            continue
        if df[column].nunique(dropna=True) <= 1:
            continue
        safe.append(column)
    return safe


def prepare_X_y(df: pd.DataFrame, feature_columns: list[str]):
    X = df[feature_columns].copy().apply(pd.to_numeric, errors="coerce")
    y = df[TARGET_COLUMN].astype(int)
    return X, y


def prepare_fixture_X(fixtures_df: pd.DataFrame, feature_columns: list[str]):
    predictable = fixtures_df[fixtures_df.get("is_predictable_now", False).astype(bool)].copy()
    for column in feature_columns:
        if column not in predictable.columns:
            predictable[column] = pd.NA
    X_fixture = predictable[feature_columns].copy().apply(pd.to_numeric, errors="coerce")
    metadata_cols = [c for c in ["match_id", "date", "team_a", "team_b", "stage", "group", "venue", "status", "is_predictable_now"] if c in predictable.columns]
    return X_fixture, predictable[metadata_cols].copy()


def save_selected_features(feature_columns: list[str]) -> dict:
    ensure_modeling_directories()
    txt_path = MODELING_REPORT_DIR / "selected_feature_columns.txt"
    csv_path = MODELING_REPORT_DIR / "selected_feature_columns.csv"
    txt_path.write_text("\n".join(feature_columns), encoding="utf-8")
    pd.DataFrame({"feature": feature_columns}).to_csv(csv_path, index=False)
    return {"txt": str(txt_path), "csv": str(csv_path)}
