"""Load and summarize modeling datasets."""

from __future__ import annotations

import pandas as pd

from src.modeling.model_config import FIXTURE_FEATURES_PATH, MODELING_REPORT_DIR, TARGET_COLUMN, TRAINING_DATASET_PATH, ensure_modeling_directories


def load_training_dataset() -> pd.DataFrame:
    df = pd.read_csv(TRAINING_DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")
    df = df.dropna(subset=[TARGET_COLUMN]).copy()
    df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    df = df[df[TARGET_COLUMN].isin([0, 1, 2])].copy()
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
    return df


def load_fixture_features() -> tuple[pd.DataFrame, pd.DataFrame]:
    fixtures = pd.read_csv(FIXTURE_FEATURES_PATH)
    if "date" in fixtures.columns:
        fixtures["date"] = pd.to_datetime(fixtures["date"], errors="coerce")
    predictable = fixtures[fixtures.get("is_predictable_now", False).astype(bool)].copy()
    return fixtures, predictable


def summarize_modeling_data(training_df: pd.DataFrame | None = None, fixtures_df: pd.DataFrame | None = None) -> str:
    ensure_modeling_directories()
    training_df = training_df if training_df is not None else load_training_dataset()
    fixtures_df = fixtures_df if fixtures_df is not None else load_fixture_features()[0]
    predictable_count = int(fixtures_df.get("is_predictable_now", pd.Series(dtype=bool)).fillna(False).sum())
    distribution = training_df[TARGET_COLUMN].value_counts(normalize=False).sort_index()
    lines = [
        "# Modeling Data Summary",
        "",
        f"- Training rows: {len(training_df)}",
        f"- Fixture rows: {len(fixtures_df)}",
        f"- Predictable fixture rows: {predictable_count}",
        f"- Date range: {training_df['date'].min()} to {training_df['date'].max()}",
        f"- Candidate columns: {len(training_df.columns)}",
        "",
        "## Target Distribution",
        "",
    ]
    for class_id, count in distribution.items():
        lines.append(f"- `{class_id}`: {count}")
    path = MODELING_REPORT_DIR / "modeling_data_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
