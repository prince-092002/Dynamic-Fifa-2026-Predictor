"""Detect obvious feature leakage risks."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_REPORT_DIR, MODEL_FEATURE_COLUMNS, TARGET_COLUMNS, TRAINING_DATASET_PATH, ensure_feature_directories


def run_leakage_checks() -> dict:
    ensure_feature_directories()
    checks = []
    suspicious_terms = ["post_match", "future", "team_a_goals_for_current", "team_b_goals_for_current"]
    if not TRAINING_DATASET_PATH.exists():
        checks.append(("training_file_exists", "fail", "Training feature file is missing."))
    else:
        df = pd.read_csv(TRAINING_DATASET_PATH, nrows=100)
        target_inside_features = [c for c in TARGET_COLUMNS if c in MODEL_FEATURE_COLUMNS]
        checks.append(("target_columns_not_in_feature_list", "pass" if not target_inside_features else "fail", str(target_inside_features)))
        suspicious = [c for c in df.columns if any(term in c.lower() for term in suspicious_terms)]
        checks.append(("suspicious_column_names", "pass" if not suspicious else "warn", str(suspicious)))
        pre_match = {"team_a_pre_match_elo", "team_b_pre_match_elo"}.issubset(df.columns)
        checks.append(("pre_match_elo_present", "pass" if pre_match else "fail", "Historical Elo features should be pre-match."))
        current_rating_cols = [c for c in df.columns if c in {"team_a_fifa_rank", "team_b_fifa_rank", "team_a_fifa_points", "team_b_fifa_points"}]
        checks.append(("current_ratings_not_in_historical_training", "pass" if not current_rating_cols else "warn", str(current_rating_cols)))
    md_path = FEATURE_REPORT_DIR / "leakage_check_report.md"
    lines = ["# Leakage Check Report", "", "| Check | Status | Notes |", "|---|---|---|"]
    for check, status, notes in checks:
        lines.append(f"| {check} | {status} | {notes.replace('|', '\\|')} |")
    failed = [check for check in checks if check[1] == "fail"]
    lines.extend(["", "## Recommended Fixes", ""])
    if failed:
        lines.append("Fix failed checks before modeling.")
    else:
        lines.append("No major leakage failures detected. Review warnings before modeling.")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "fail" if failed else "pass", "report": str(md_path)}
