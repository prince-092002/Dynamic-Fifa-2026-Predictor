"""Reports and validation for live knockout matchup predictions."""

from __future__ import annotations

import json

import pandas as pd

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, coerce_bool_series, ensure_live_directories
from src.live_state.live_matchup_features import KNOCKOUT_STAGES, LIVE_FEATURES_PATH, REMAINING_MATCHUPS_PATH
from src.live_state.live_matchup_predictor import LIVE_PREDICTIONS_PATH
from src.modeling.predict_fixtures import _load_feature_columns
from src.simulation.tournament_structure import is_tbd_team
from src.utils.dates import now_utc_iso

SOURCE_COUNTS_PATH = LIVE_STATE_DIR / "live_probability_source_counts.json"
PREVIOUS_SOURCE_COUNTS_PATH = LIVE_STATE_DIR / "live_probability_source_counts_previous.json"
PREDICTION_REPORT_PATH = LIVE_REPORT_DIR / "live_knockout_prediction_report.md"
PREDICTION_VALIDATION_PATH = LIVE_REPORT_DIR / "live_knockout_prediction_validation.md"


def _read_csv(path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _fallback_share(counts: dict) -> float:
    total = sum(counts.values())
    return (counts.get("elo_fallback", 0) + counts.get("neutral_fallback", 0)) / total if total else 0.0


def _bracket_skip_counts() -> dict:
    bracket = _read_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
    if bracket.empty:
        return {"completed": 0, "tbd": 0}
    knockout = bracket[bracket["stage"].astype(str).isin(KNOCKOUT_STAGES)]
    completed = coerce_bool_series(knockout.get("is_completed", pd.Series(False, index=knockout.index)))
    tbd = knockout.apply(lambda row: is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")) or pd.isna(row.get("team_a")) or pd.isna(row.get("team_b")), axis=1)
    return {"completed": int(completed.sum()), "tbd": int((~completed & tbd).sum())}


def write_live_knockout_prediction_report() -> str:
    ensure_live_directories()
    matchups = _read_csv(REMAINING_MATCHUPS_PATH)
    features = _read_csv(LIVE_FEATURES_PATH)
    predictions = _read_csv(LIVE_PREDICTIONS_PATH)
    counts = _read_json(SOURCE_COUNTS_PATH)
    previous_counts = _read_json(PREVIOUS_SOURCE_COUNTS_PATH)
    skips = _bracket_skip_counts()
    predicted = predictions[predictions.get("prediction_status", "") == "predicted"] if not predictions.empty else pd.DataFrame()
    model_name = predictions["model_name"].dropna().iloc[0] if not predictions.empty and predictions["model_name"].notna().any() else "unknown"
    lines = [
        "# Live Knockout Prediction Report",
        "",
        f"- Generated: {now_utc_iso()}",
        f"- Known remaining knockout matchups: {len(matchups)}",
        f"- Predicted by live model: {len(predicted)}",
        f"- Failed (missing features): {len(predictions) - len(predicted) if not predictions.empty else 0}",
        f"- Knockout matches skipped because they are completed: {skips['completed']}",
        f"- Knockout matches skipped because participants are TBD: {skips['tbd']}",
        f"- Model used: {model_name}",
        "",
        "## Feature Completeness",
        "",
    ]
    if features.empty:
        lines.append("No live knockout feature rows were generated.")
    else:
        for _, row in features.iterrows():
            lines.append(f"- {row.get('team_a')} vs {row.get('team_b')} ({row.get('stage')}): {row.get('feature_status')} ({row.get('missing_feature_count')} missing feature values)")
    lines.extend(["", "## Live Model Predictions", "", "| Stage | Match | P(team A win) | P(draw) | P(team A loss) | P(A advances) | Source | Status |", "|---|---|---:|---:|---:|---:|---|---|"])
    if predictions.empty:
        lines.append("| - | No predictions generated | - | - | - | - | - | - |")
    else:
        for _, row in predictions.iterrows():
            if row.get("prediction_status") == "predicted":
                lines.append(
                    f"| {row.get('stage')} | {row.get('team_a')} vs {row.get('team_b')} | {float(row['prob_team_a_win']):.4f} | {float(row['prob_draw']):.4f} "
                    f"| {float(row['prob_team_a_loss']):.4f} | {float(row['prob_team_a_advance']):.4f} | {row.get('probability_source')} | {row.get('prediction_status')} |"
                )
            else:
                lines.append(f"| {row.get('stage')} | {row.get('team_a')} vs {row.get('team_b')} | - | - | - | - | - | {row.get('prediction_status')} |")
    lines.extend(["", "## Probability Source Usage (simulated matches)", "", "| Source | Previous run | Latest run |", "|---|---:|---:|"])
    for source in sorted(set(previous_counts) | set(counts)):
        lines.append(f"| {source} | {previous_counts.get(source, 0)} | {counts.get(source, 0)} |")
    before = _fallback_share(previous_counts)
    after = _fallback_share(counts)
    lines.extend(
        [
            "",
            f"- Elo/neutral fallback share before: {before:.2%}" if previous_counts else "- Elo/neutral fallback share before: not recorded",
            f"- Elo/neutral fallback share after: {after:.2%}" if counts else "- Elo/neutral fallback share after: not recorded",
            f"- Fallback reduction: {before - after:+.2%}" if previous_counts and counts else "- Fallback reduction: not measurable yet",
            "",
            "## Remaining Limitations",
            "",
            "- Semifinal/final matchups stay on Elo fallback inside each simulation until their participants are known in the real bracket.",
            "- Live model predictions reuse pre-tournament feature definitions; they are regenerated per round, not per simulation branch.",
            "- Elo fallback remains as backup and is always labeled as fallback, never as a model prediction.",
        ]
    )
    PREDICTION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return str(PREDICTION_REPORT_PATH)


def validate_live_knockout_predictions() -> dict:
    ensure_live_directories()
    matchups = _read_csv(REMAINING_MATCHUPS_PATH)
    features = _read_csv(LIVE_FEATURES_PATH)
    predictions = _read_csv(LIVE_PREDICTIONS_PATH)
    counts = _read_json(SOURCE_COUNTS_PATH)
    previous_counts = _read_json(PREVIOUS_SOURCE_COUNTS_PATH)
    fixtures = _read_csv(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
    checks: list[tuple[str, str, str]] = []

    checks.append(("matchup_file_exists", "pass" if REMAINING_MATCHUPS_PATH.exists() else "fail", str(REMAINING_MATCHUPS_PATH)))
    checks.append(("known_unplayed_matchups_detected", "pass" if not matchups.empty else "warn", f"{len(matchups)} matchups"))
    checks.append(("feature_file_exists", "pass" if LIVE_FEATURES_PATH.exists() else "fail", str(LIVE_FEATURES_PATH)))
    expected_features = _load_feature_columns()
    missing_columns = [c for c in expected_features if c not in features.columns] if not features.empty else expected_features
    checks.append(("feature_columns_match_model", "pass" if not missing_columns else "fail", f"missing: {missing_columns[:6]}" if missing_columns else "all model feature columns present"))

    predicted = predictions[predictions.get("prediction_status", "") == "predicted"] if not predictions.empty else pd.DataFrame()
    prob_cols = ["prob_team_a_loss", "prob_draw", "prob_team_a_win"]
    if predicted.empty:
        checks.append(("probabilities_in_range", "warn", "no predicted rows"))
        checks.append(("probabilities_sum_to_one", "warn", "no predicted rows"))
        checks.append(("advancement_probabilities_sum_to_one", "warn", "no predicted rows"))
    else:
        probs = predicted[prob_cols].apply(pd.to_numeric, errors="coerce")
        in_range = bool(((probs >= 0) & (probs <= 1)).all().all())
        checks.append(("probabilities_in_range", "pass" if in_range else "fail", "all probabilities within [0, 1]" if in_range else "out-of-range probability found"))
        sums = probs.sum(axis=1)
        sums_ok = bool(((sums - 1).abs() <= 0.01).all())
        checks.append(("probabilities_sum_to_one", "pass" if sums_ok else "fail", f"max deviation {float((sums - 1).abs().max()):.5f}"))
        adv = predicted[["prob_team_a_advance", "prob_team_b_advance"]].apply(pd.to_numeric, errors="coerce").sum(axis=1)
        adv_ok = bool(((adv - 1).abs() <= 0.01).all())
        checks.append(("advancement_probabilities_sum_to_one", "pass" if adv_ok else "fail", f"max deviation {float((adv - 1).abs().max()):.5f}"))

    completed_ids = set()
    if not fixtures.empty:
        completed_mask = coerce_bool_series(fixtures.get("is_completed", pd.Series(False, index=fixtures.index)))
        completed_ids = set(fixtures.loc[completed_mask, "match_id"].astype(str))
    predicted_completed = int(predicted["match_id"].astype(str).isin(completed_ids).sum()) if not predicted.empty else 0
    checks.append(("completed_matches_not_predicted", "pass" if predicted_completed == 0 else "fail", f"{predicted_completed} completed matches predicted"))
    tbd_predicted = 0
    if not predicted.empty:
        tbd_predicted = int(predicted.apply(lambda row: is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")) or pd.isna(row.get("team_a")) or pd.isna(row.get("team_b")), axis=1).sum())
    checks.append(("tbd_matches_not_predicted", "pass" if tbd_predicted == 0 else "fail", f"{tbd_predicted} TBD matches predicted"))

    live_usage = counts.get("live_model_exact", 0) + counts.get("live_model_reversed", 0)
    if predicted.empty:
        checks.append(("live_model_source_used_in_simulation", "warn", "no live predictions exist, so simulator fallback is expected"))
    else:
        checks.append(("live_model_source_used_in_simulation", "pass" if live_usage > 0 else "fail", f"live_model_exact + live_model_reversed = {live_usage}"))
    if previous_counts and counts:
        before = _fallback_share(previous_counts)
        after = _fallback_share(counts)
        checks.append(("elo_fallback_usage_decreased", "pass" if after < before else "warn", f"fallback share {before:.2%} -> {after:.2%}"))
    else:
        checks.append(("elo_fallback_usage_decreased", "warn", "previous source counts not recorded yet"))

    lines = ["# Live Knockout Prediction Validation", "", f"- Generated: {now_utc_iso()}", "", "| Check | Status | Message |", "|---|---|---|"]
    for check, status, message in checks:
        lines.append(f"| {check} | {status} | {message} |")
    PREDICTION_VALIDATION_PATH.write_text("\n".join(lines), encoding="utf-8")
    failed = [c for c in checks if c[1] == "fail"]
    return {"status": "fail" if failed else "pass", "report": str(PREDICTION_VALIDATION_PATH), "checks": checks}
