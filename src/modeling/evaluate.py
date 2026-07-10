"""Model evaluation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_recall_fscore_support

from src.modeling.model_config import MODELING_REPORT_DIR, ensure_modeling_directories

CLASSES = [0, 1, 2]


def align_proba(y_proba, classes) -> np.ndarray:
    aligned = np.zeros((len(y_proba), len(CLASSES)))
    class_to_idx = {int(cls): idx for idx, cls in enumerate(classes)}
    for target_idx, cls in enumerate(CLASSES):
        if cls in class_to_idx:
            aligned[:, target_idx] = y_proba[:, class_to_idx[cls]]
    row_sums = aligned.sum(axis=1)
    aligned[row_sums == 0] = 1 / len(CLASSES)
    row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def multiclass_brier_score(y_true, y_proba) -> float:
    y_true = np.asarray(y_true)
    y_one_hot = np.zeros_like(y_proba, dtype=float)
    for idx, cls in enumerate(CLASSES):
        y_one_hot[:, idx] = (y_true == cls).astype(float)
    return float(np.mean(np.sum((y_proba - y_one_hot) ** 2, axis=1)))


def evaluate_model(name: str, split: str, y_true, y_pred, y_proba) -> dict:
    precision, recall, _, _ = precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, zero_division=0)
    metrics = {
        "model": name,
        "split": split,
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "log_loss": log_loss(y_true, y_proba, labels=CLASSES),
        "brier_score": multiclass_brier_score(y_true, y_proba),
        "precision_class_0": precision[0],
        "precision_class_1": precision[1],
        "precision_class_2": precision[2],
        "recall_class_0": recall[0],
        "recall_class_1": recall[1],
        "recall_class_2": recall[2],
    }
    cm = pd.DataFrame(confusion_matrix(y_true, y_pred, labels=CLASSES), index=CLASSES, columns=CLASSES)
    cm.to_csv(MODELING_REPORT_DIR / f"confusion_matrix_{name}_{split}.csv")
    return metrics


def compare_models(metrics_list: list[dict]) -> dict:
    ensure_modeling_directories()
    df = pd.DataFrame(metrics_list)
    metrics_path = MODELING_REPORT_DIR / "model_metrics.csv"
    comparison_path = MODELING_REPORT_DIR / "model_comparison.md"
    df.to_csv(metrics_path, index=False)
    val_df = df[df["split"] == "validation"].sort_values("log_loss")
    selected = val_df.iloc[0]["model"] if not val_df.empty else ""
    lines = [
        "# Model Comparison",
        "",
        f"- Selected by lowest validation log loss: `{selected}`",
        "- Probability metrics, especially log loss and Brier score, should matter more than accuracy.",
        "",
        "| Model | Split | Accuracy | Macro F1 | Log loss | Brier score |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, row in df.iterrows():
        lines.append(f"| {row['model']} | {row['split']} | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | {row['log_loss']:.4f} | {row['brier_score']:.4f} |")
    comparison_path.write_text("\n".join(lines), encoding="utf-8")
    return {"selected_model": selected, "metrics_csv": str(metrics_path), "comparison": str(comparison_path)}
