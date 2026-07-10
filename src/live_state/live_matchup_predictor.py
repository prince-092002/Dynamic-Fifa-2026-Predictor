"""Predict resolved live knockout matchups with the selected trained model."""

from __future__ import annotations

import joblib
import pandas as pd

from src.live_state.live_config import LIVE_STATE_DIR, ensure_live_directories
from src.live_state.live_matchup_features import LIVE_FEATURES_PATH, build_live_knockout_features, identify_remaining_live_knockout_matches
from src.modeling.evaluate import CLASSES, align_proba
from src.modeling.model_config import MODEL_DIR
from src.modeling.predict_fixtures import LABELS, _load_feature_columns, _load_selected_model_name
from src.utils.dates import now_utc_iso

LIVE_PREDICTIONS_PATH = LIVE_STATE_DIR / "live_knockout_match_predictions.csv"

PREDICTION_COLUMNS = [
    "fixture_id",
    "match_id",
    "stage",
    "team_a",
    "team_b",
    "prob_team_a_loss",
    "prob_draw",
    "prob_team_a_win",
    "prob_team_a_advance",
    "prob_team_b_advance",
    "predicted_result_label",
    "confidence",
    "model_name",
    "prediction_status",
    "probability_source",
    "generated_at",
]


def predict_live_knockout_matchups() -> dict:
    """Run the selected model on live knockout matchup features."""
    ensure_live_directories()
    features = pd.read_csv(LIVE_FEATURES_PATH) if LIVE_FEATURES_PATH.exists() else pd.DataFrame()
    if features.empty:
        features = build_live_knockout_features()
    model_name = _load_selected_model_name()
    feature_columns = _load_feature_columns()
    model_path = MODEL_DIR / "selected_model.joblib"
    output = features[[c for c in ["fixture_id", "match_id", "stage", "team_a", "team_b"] if c in features.columns]].copy()
    for column in ["prob_team_a_loss", "prob_draw", "prob_team_a_win", "prob_team_a_advance", "prob_team_b_advance", "predicted_result_label", "confidence"]:
        output[column] = pd.NA
    output["model_name"] = model_name
    output["prediction_status"] = "failed_missing_features"
    output["probability_source"] = "live_model"
    output["generated_at"] = now_utc_iso()
    if features.empty or not model_path.exists() or not feature_columns:
        output = output.reindex(columns=PREDICTION_COLUMNS)
        output.to_csv(LIVE_PREDICTIONS_PATH, index=False)
        return {"predictions_path": str(LIVE_PREDICTIONS_PATH), "predicted_rows": 0, "failed_rows": len(output), "model_name": model_name}
    model = joblib.load(model_path)
    predictable = features[features.get("is_predictable_now", pd.Series(True, index=features.index)).astype(bool)].copy()
    if not predictable.empty:
        for column in feature_columns:
            if column not in predictable.columns:
                predictable[column] = pd.NA
        X = predictable[feature_columns].apply(pd.to_numeric, errors="coerce")
        proba = model.predict_proba(X)
        classes = getattr(model, "classes_", CLASSES)
        if hasattr(model, "named_steps"):
            classes = model.named_steps["model"].classes_
        proba = align_proba(proba, classes)
        pred = proba.argmax(axis=1)
        for idx, match_id in enumerate(predictable["match_id"].tolist()):
            mask = output["match_id"] == match_id
            loss, draw, win = float(proba[idx, 0]), float(proba[idx, 1]), float(proba[idx, 2])
            output.loc[mask, "prob_team_a_loss"] = loss
            output.loc[mask, "prob_draw"] = draw
            output.loc[mask, "prob_team_a_win"] = win
            output.loc[mask, "prob_team_a_advance"] = win + 0.5 * draw
            output.loc[mask, "prob_team_b_advance"] = loss + 0.5 * draw
            output.loc[mask, "predicted_result_label"] = LABELS[int(pred[idx])]
            output.loc[mask, "confidence"] = float(proba[idx].max())
            output.loc[mask, "prediction_status"] = "predicted"
    output = output.reindex(columns=PREDICTION_COLUMNS)
    output.to_csv(LIVE_PREDICTIONS_PATH, index=False)
    predicted_rows = int((output["prediction_status"] == "predicted").sum())
    return {
        "predictions_path": str(LIVE_PREDICTIONS_PATH),
        "predicted_rows": predicted_rows,
        "failed_rows": int(len(output) - predicted_rows),
        "model_name": model_name,
    }


def load_live_knockout_prediction_lookup() -> dict:
    """Team-pair probability lookup from successful live model predictions."""
    if not LIVE_PREDICTIONS_PATH.exists():
        return {}
    predictions = pd.read_csv(LIVE_PREDICTIONS_PATH)
    if predictions.empty:
        return {}
    lookup = {}
    for _, row in predictions[predictions.get("prediction_status", "") == "predicted"].iterrows():
        key = (str(row["team_a"]), str(row["team_b"]))
        lookup[key] = (float(row["prob_team_a_loss"]), float(row["prob_draw"]), float(row["prob_team_a_win"]))
    return lookup


def run_live_knockout_prediction_flow() -> dict:
    """Identify matchups, build features, and predict them in one step."""
    matchups = identify_remaining_live_knockout_matches()
    features = build_live_knockout_features()
    prediction_result = predict_live_knockout_matchups()
    return {
        "matchup_count": len(matchups),
        "feature_rows": len(features),
        "predicted_rows": prediction_result["predicted_rows"],
        "failed_rows": prediction_result["failed_rows"],
        "model_name": prediction_result["model_name"],
        "predictions_path": prediction_result["predictions_path"],
    }
