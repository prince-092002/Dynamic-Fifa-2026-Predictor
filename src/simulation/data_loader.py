"""Load simulation inputs."""

from __future__ import annotations

import pandas as pd

from src.simulation.simulation_config import (
    PREDICTION_FILE_PATH,
    PROCESSED_FIXTURES_PATH,
    PROCESSED_RESULTS_PATH,
    SIMULATION_REPORT_DIR,
    ensure_simulation_directories,
)


def load_fixture_predictions() -> pd.DataFrame:
    if not PREDICTION_FILE_PATH.exists():
        raise FileNotFoundError(f"Missing prediction file: {PREDICTION_FILE_PATH}")
    df = pd.read_csv(PREDICTION_FILE_PATH)
    required = ["prob_team_a_loss", "prob_draw", "prob_team_a_win"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Prediction file is missing probability columns: {missing}")
    return df


def load_fixtures() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_FIXTURES_PATH) if PROCESSED_FIXTURES_PATH.exists() else pd.DataFrame()


def load_results() -> pd.DataFrame:
    if not PROCESSED_RESULTS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(PROCESSED_RESULTS_PATH)
    return df if not df.empty else pd.DataFrame()


def load_simulation_inputs() -> dict:
    ensure_simulation_directories()
    predictions = load_fixture_predictions()
    fixtures = load_fixtures()
    results = load_results()
    predicted_count = int((predictions.get("prediction_status", "") == "predicted").sum())
    not_predicted = len(predictions) - predicted_count
    missing_probs = int(predictions[["prob_team_a_loss", "prob_draw", "prob_team_a_win"]].isna().any(axis=1).sum())
    stages = predictions.get("stage", pd.Series(dtype=object)).dropna().unique().tolist()
    lines = [
        "# Simulation Input Summary",
        "",
        f"- Total fixture prediction rows: {len(predictions)}",
        f"- Predicted fixture rows: {predicted_count}",
        f"- Not predictable rows: {not_predicted}",
        f"- Completed result rows: {len(results)}",
        f"- Stages available: {', '.join(map(str, stages))}",
        f"- Rows with missing probabilities: {missing_probs}",
    ]
    path = SIMULATION_REPORT_DIR / "simulation_input_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"predictions": predictions, "fixtures": fixtures, "results": results, "report": str(path)}
