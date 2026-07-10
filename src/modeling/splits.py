"""Chronological train/validation/test splitting."""

from __future__ import annotations

import pandas as pd

from src.modeling.model_config import MODELING_REPORT_DIR, TARGET_COLUMN, TRAIN_FRACTION, VAL_FRACTION, ensure_modeling_directories


def _range_text(df: pd.DataFrame) -> str:
    return f"{df['date'].min()} to {df['date'].max()}" if not df.empty else "empty"


def chronological_train_val_test_split(df: pd.DataFrame):
    ensure_modeling_directories()
    ordered = df.sort_values("date").reset_index(drop=True)
    n = len(ordered)
    train_end = int(n * TRAIN_FRACTION)
    val_end = int(n * (TRAIN_FRACTION + VAL_FRACTION))
    train_df = ordered.iloc[:train_end].copy()
    val_df = ordered.iloc[train_end:val_end].copy()
    test_df = ordered.iloc[val_end:].copy()
    lines = ["# Split Report", "", "| Split | Rows | Date range | Target distribution |", "|---|---:|---|---|"]
    for name, part in [("train", train_df), ("validation", val_df), ("test", test_df)]:
        dist = part[TARGET_COLUMN].value_counts().sort_index().to_dict()
        lines.append(f"| {name} | {len(part)} | {_range_text(part)} | {dist} |")
    path = MODELING_REPORT_DIR / "split_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return train_df, val_df, test_df
