"""Generate FIFA 2026 fixture predictions from the selected model."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import pandas as pd

from src.modeling.evaluate import CLASSES, align_proba
from src.modeling.feature_selection import prepare_fixture_X
from src.modeling.model_config import FIXTURE_FEATURES_PATH, MODEL_DIR, MODELING_REPORT_DIR, PREDICTION_DIR, ensure_modeling_directories

LABELS = {0: "team_a_loss", 1: "draw", 2: "team_a_win"}


def _load_feature_columns() -> list[str]:
    registry_path = MODEL_DIR / "model_registry.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        selected = next((item for item in registry.get("models", []) if item.get("selected_model")), None)
        if selected:
            return selected.get("feature_columns", [])
    selected_features = MODELING_REPORT_DIR / "selected_feature_columns.txt"
    return selected_features.read_text(encoding="utf-8").splitlines() if selected_features.exists() else []


def _load_selected_model_name() -> str:
    registry_path = MODEL_DIR / "model_registry.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        selected = next((item for item in registry.get("models", []) if item.get("selected_model")), None)
        if selected:
            return selected.get("model_name", "selected_model")
    return "selected_model"


def predict_fixtures(model_name: str | None = None) -> dict:
    ensure_modeling_directories()
    model_name = model_name or _load_selected_model_name()
    fixtures = pd.read_csv(FIXTURE_FEATURES_PATH)
    feature_columns = _load_feature_columns()
    model_path = MODEL_DIR / "selected_model.joblib"
    model = joblib.load(model_path)
    output = fixtures[[c for c in ["match_id", "date", "team_a", "team_b", "stage", "group", "venue", "status", "is_predictable_now"] if c in fixtures.columns]].copy()
    for column in ["prob_team_a_loss", "prob_draw", "prob_team_a_win", "predicted_result", "predicted_result_label", "confidence"]:
        output[column] = pd.NA
    output["model_name"] = model_name
    output["prediction_timestamp"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    output["prediction_status"] = "not_predictable_tbd_or_missing_features"
    X_fixture, metadata = prepare_fixture_X(fixtures, feature_columns)
    if not X_fixture.empty:
        proba = model.predict_proba(X_fixture)
        classes = getattr(model, "classes_", CLASSES)
        if hasattr(model, "named_steps"):
            classes = model.named_steps["model"].classes_
        proba = align_proba(proba, classes)
        pred = proba.argmax(axis=1)
        for idx, match_id in enumerate(metadata["match_id"].tolist()):
            mask = output["match_id"] == match_id
            output.loc[mask, "prob_team_a_loss"] = proba[idx, 0]
            output.loc[mask, "prob_draw"] = proba[idx, 1]
            output.loc[mask, "prob_team_a_win"] = proba[idx, 2]
            output.loc[mask, "predicted_result"] = int(pred[idx])
            output.loc[mask, "predicted_result_label"] = LABELS[int(pred[idx])]
            output.loc[mask, "confidence"] = float(proba[idx].max())
            output.loc[mask, "prediction_status"] = "predicted"
    path = PREDICTION_DIR / "fixture_2026_match_predictions.csv"
    output.to_csv(path, index=False)
    report = write_fixture_prediction_summary(output, model_name)
    return {"predictions": str(path), "report": report, "predicted_rows": int((output["prediction_status"] == "predicted").sum())}


def write_fixture_prediction_summary(predictions: pd.DataFrame, model_name: str) -> str:
    predicted = predictions[predictions["prediction_status"] == "predicted"].copy()
    lines = [
        "# Fixture Prediction Summary",
        "",
        f"- Model used: {model_name}",
        f"- Total fixtures: {len(predictions)}",
        f"- Predictable fixtures: {len(predicted)}",
        f"- Not predictable fixtures: {len(predictions) - len(predicted)}",
        "",
        "## Top 10 Highest Confidence",
        "",
    ]
    if not predicted.empty:
        for _, row in predicted.sort_values("confidence", ascending=False).head(10).iterrows():
            lines.append(f"- {row.get('team_a')} vs {row.get('team_b')}: {row.get('predicted_result_label')} ({float(row.get('confidence')):.3f})")
        lines.extend(["", "## Top 10 Most Uncertain", ""])
        for _, row in predicted.sort_values("confidence", ascending=True).head(10).iterrows():
            lines.append(f"- {row.get('team_a')} vs {row.get('team_b')}: {row.get('predicted_result_label')} ({float(row.get('confidence')):.3f})")
    path = MODELING_REPORT_DIR / "fixture_prediction_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
