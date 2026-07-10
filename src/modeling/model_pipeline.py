"""Full modeling pipeline orchestration."""

from __future__ import annotations

import joblib

from src.modeling.baselines import predict_model, train_elo_logistic_baseline, train_frequency_baseline, train_majority_baseline
from src.modeling.calibration import write_calibration_report
from src.modeling.data_loader import load_fixture_features, load_training_dataset, summarize_modeling_data
from src.modeling.evaluate import align_proba, compare_models, evaluate_model
from src.modeling.feature_selection import get_safe_feature_columns, prepare_X_y, save_selected_features
from src.modeling.model_config import MODEL_DIR, RANDOM_SEED, ensure_modeling_directories
from src.modeling.model_registry import write_model_registry
from src.modeling.model_reports import write_modeling_phase_summary
from src.modeling.predict_fixtures import predict_fixtures
from src.modeling.splits import chronological_train_val_test_split
from src.modeling.train_logistic import train_logistic_regression
from src.modeling.train_xgboost import train_xgboost_model


def _evaluate_saved_model(name, model, X_val, y_val, X_test, y_test):
    rows = []
    for split, X, y in [("validation", X_val, y_val), ("test", X_test, y_test)]:
        proba = model.predict_proba(X)
        classes = getattr(model, "classes_", [0, 1, 2])
        if hasattr(model, "named_steps"):
            classes = model.named_steps["model"].classes_
        proba = align_proba(proba, classes)
        pred = proba.argmax(axis=1)
        rows.append(evaluate_model(name, split, y, pred, proba))
    return rows


def run_modeling_pipeline() -> dict:
    ensure_modeling_directories()
    training_df = load_training_dataset()
    fixtures_df, _ = load_fixture_features()
    data_summary = summarize_modeling_data(training_df, fixtures_df)
    feature_columns = get_safe_feature_columns(training_df)
    save_selected_features(feature_columns)
    train_df, val_df, test_df = chronological_train_val_test_split(training_df)
    X_train, y_train = prepare_X_y(train_df, feature_columns)
    X_val, y_val = prepare_X_y(val_df, feature_columns)
    X_test, y_test = prepare_X_y(test_df, feature_columns)

    metrics = []
    model_entries = []

    baselines = {
        "majority_class_baseline": train_majority_baseline(y_train),
        "historical_frequency_baseline": train_frequency_baseline(y_train),
    }
    elo_model, elo_issue = train_elo_logistic_baseline(train_df)
    if elo_model is not None:
        baselines["elo_logistic_baseline"] = elo_model
    for name, model in baselines.items():
        Xv = val_df[["elo_difference"]] if name == "elo_logistic_baseline" else X_val
        Xt = test_df[["elo_difference"]] if name == "elo_logistic_baseline" else X_test
        for split, X, y in [("validation", Xv, y_val), ("test", Xt, y_test)]:
            pred, proba = predict_model(model, X)
            metrics.append(evaluate_model(name, split, y, pred, proba))

    logistic, logistic_path = train_logistic_regression(X_train, y_train)
    metrics.extend(_evaluate_saved_model("logistic_regression", logistic, X_val, y_val, X_test, y_test))
    model_entries.append({"model_name": "logistic_regression", "model_type": "LogisticRegression", "model_file_path": logistic_path})

    xgb, xgb_path = train_xgboost_model(X_train, y_train, X_val, y_val, feature_columns)
    metrics.extend(_evaluate_saved_model("xgboost", xgb, X_val, y_val, X_test, y_test))
    model_entries.append({"model_name": "xgboost", "model_type": "XGBClassifier", "model_file_path": xgb_path})

    comparison = compare_models(metrics)
    selected_model = comparison["selected_model"]
    if selected_model not in {"logistic_regression", "xgboost"}:
        selected_model = "logistic_regression"
    val_metric = next(row for row in metrics if row["model"] == selected_model and row["split"] == "validation")
    test_metric = next(row for row in metrics if row["model"] == selected_model and row["split"] == "test")
    for entry in model_entries:
        entry_val_metric = next((row for row in metrics if row["model"] == entry["model_name"] and row["split"] == "validation"), {})
        entry_test_metric = next((row for row in metrics if row["model"] == entry["model_name"] and row["split"] == "test"), {})
        entry.update(
            {
                "feature_columns": feature_columns,
                "train_rows": len(train_df),
                "validation_rows": len(val_df),
                "test_rows": len(test_df),
                "validation_metrics": entry_val_metric,
                "test_metrics": entry_test_metric,
                "notes": f"Random seed {RANDOM_SEED}. Baseline issue: {elo_issue}",
            }
        )
    registry = write_model_registry(model_entries, selected_model)
    calibration = write_calibration_report(False)
    predictions = predict_fixtures(selected_model)
    phase_summary = write_modeling_phase_summary()
    return {
        "status": "success",
        "selected_model": selected_model,
        "validation_log_loss": val_metric["log_loss"],
        "test_log_loss": test_metric["log_loss"],
        "fixture_predictions_path": predictions["predictions"],
        "reports": [data_summary, comparison["comparison"], calibration, predictions["report"], phase_summary, registry["registry"]],
    }
