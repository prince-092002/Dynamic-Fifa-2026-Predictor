"""Modeling phase reports."""

from __future__ import annotations

import json

import pandas as pd

from src.modeling.model_config import MODEL_DIR, MODELING_REPORT_DIR, PREDICTION_DIR, ensure_modeling_directories


def write_modeling_phase_summary() -> str:
    ensure_modeling_directories()
    metrics_path = MODELING_REPORT_DIR / "model_metrics.csv"
    predictions_path = PREDICTION_DIR / "fixture_2026_match_predictions.csv"
    registry_path = MODEL_DIR / "model_registry.json"
    metrics = pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame()
    predictions = pd.read_csv(predictions_path) if predictions_path.exists() else pd.DataFrame()
    selected = ""
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        selected = next((item.get("model_name") for item in registry.get("models", []) if item.get("selected_model")), "")
    best_val = metrics[(metrics["model"] == selected) & (metrics["split"] == "validation")].to_dict("records") if not metrics.empty and selected else []
    best_test = metrics[(metrics["model"] == selected) & (metrics["split"] == "test")].to_dict("records") if not metrics.empty and selected else []
    lines = [
        "# Modeling Phase Summary",
        "",
        f"- Best model selected: {selected or 'unknown'}",
        f"- Prediction output path: `{predictions_path}`",
        f"- Fixture predictions rows: {len(predictions)}",
        f"- Predicted fixture rows: {int((predictions.get('prediction_status', pd.Series(dtype=str)) == 'predicted').sum()) if not predictions.empty else 0}",
        f"- Validation metrics: {best_val[0] if best_val else 'not available'}",
        f"- Test metrics: {best_test[0] if best_test else 'not available'}",
        "",
        "## Limitations",
        "",
        "- FIFA 2026 results are not fully loaded while `results_2026.csv` is header-only.",
        "- Team stats/player stats are not included while their processed files are header-only.",
        "- Fixtures with TBD teams are preserved but not predicted yet.",
        "- Predictions are probabilistic, not guarantees.",
        "",
        "## Next Recommended Step",
        "",
        "Review model comparison and fixture predictions before starting Monte Carlo simulation in a separate phase.",
    ]
    path = MODELING_REPORT_DIR / "modeling_phase_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[2:8]))
    return str(path)
