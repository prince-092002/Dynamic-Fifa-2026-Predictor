"""Feature dataset validation."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import (
    FEATURE_REPORT_DIR,
    FIXTURE_FEATURES_PATH,
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMNS,
    TRAINING_DATASET_PATH,
    ensure_feature_directories,
)


def _row(dataset: str, check: str, status: str, message: str, rows_affected: int = 0) -> dict:
    return {"dataset": dataset, "check": check, "status": status, "message": message, "rows_affected": rows_affected}


def validate_training_features() -> list[dict]:
    rows = []
    if not TRAINING_DATASET_PATH.exists():
        return [_row("training", "exists", "fail", "match_training_dataset.csv is missing")]
    df = pd.read_csv(TRAINING_DATASET_PATH)
    rows.append(_row("training", "rows", "pass" if len(df) > 0 else "fail", f"{len(df)} rows", len(df)))
    required = ["match_id", "date", "team_a", "team_b", *TARGET_COLUMNS]
    missing = [c for c in required if c not in df.columns]
    rows.append(_row("training", "required_columns", "pass" if not missing else "fail", f"Missing: {missing}"))
    target_in_features = [c for c in TARGET_COLUMNS if c in MODEL_FEATURE_COLUMNS]
    rows.append(_row("training", "target_leakage_columns", "pass" if not target_in_features else "fail", f"Targets in feature list: {target_in_features}"))
    dupes = int(df["match_id"].duplicated().sum()) if "match_id" in df.columns else 0
    rows.append(_row("training", "duplicate_match_id", "pass" if dupes == 0 else "fail", f"{dupes} duplicate match IDs", dupes))
    null_feature_cols = [c for c in MODEL_FEATURE_COLUMNS if c in df.columns and df[c].isna().all()]
    rows.append(_row("training", "fully_null_feature_columns", "pass" if not null_feature_cols else "warn", f"Fully null: {null_feature_cols[:20]}", len(null_feature_cols)))
    parsed = pd.to_datetime(df.get("date"), errors="coerce")
    rows.append(_row("training", "parseable_dates", "pass" if parsed.notna().all() else "fail", f"{int(parsed.isna().sum())} invalid dates", int(parsed.isna().sum())))
    valid_results = df["match_result"].isin([0, 1, 2]).all() if "match_result" in df.columns else False
    rows.append(_row("training", "match_result_values", "pass" if valid_results else "fail", "match_result values should be 0, 1, 2"))
    return rows


def validate_fixture_features() -> list[dict]:
    rows = []
    if not FIXTURE_FEATURES_PATH.exists():
        return [_row("fixtures", "exists", "fail", "fixture_2026_features.csv is missing")]
    df = pd.read_csv(FIXTURE_FEATURES_PATH)
    rows.append(_row("fixtures", "rows", "pass" if len(df) > 0 else "fail", f"{len(df)} rows", len(df)))
    required = ["match_id", "team_a", "team_b", "fixture_has_tbd_team", "is_predictable_now"]
    missing = [c for c in required if c not in df.columns]
    rows.append(_row("fixtures", "required_columns", "pass" if not missing else "fail", f"Missing: {missing}"))
    tbd_count = int(df.get("fixture_has_tbd_team", pd.Series(dtype=bool)).fillna(False).sum()) if "fixture_has_tbd_team" in df else 0
    rows.append(_row("fixtures", "tbd_preserved", "pass", f"{tbd_count} TBD fixtures preserved", tbd_count))
    predictable = int(df.get("is_predictable_now", pd.Series(dtype=bool)).fillna(False).sum()) if "is_predictable_now" in df else 0
    rows.append(_row("fixtures", "predictable_now", "pass", f"{predictable} fixtures currently predictable", predictable))
    feature_cols = [c for c in MODEL_FEATURE_COLUMNS if c in df.columns]
    rows.append(_row("fixtures", "feature_columns", "pass" if feature_cols else "fail", f"{len(feature_cols)} configured feature columns present", len(feature_cols)))
    return rows


def run_feature_validation() -> dict:
    ensure_feature_directories()
    rows = validate_training_features() + validate_fixture_features()
    df = pd.DataFrame(rows)
    csv_path = FEATURE_REPORT_DIR / "feature_validation_report.csv"
    md_path = FEATURE_REPORT_DIR / "feature_validation_report.md"
    df.to_csv(csv_path, index=False)
    lines = ["# Feature Validation Report", "", "| Dataset | Check | Status | Message | Rows affected |", "|---|---|---|---|---:|"]
    for _, row in df.iterrows():
        lines.append(f"| {row['dataset']} | {row['check']} | {row['status']} | {str(row['message']).replace('|', '\\|')} | {row['rows_affected']} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "fail" if (df["status"] == "fail").any() else "pass", "report": str(md_path), "csv": str(csv_path)}
