"""Phase 5G — leakage-safe model diagnostics, feature optimization & challenger evaluation.

Research harness. Reproduces the production chronological split, freezes the
production XGBoost/Logistic baselines, runs diagnostics, segmented analysis,
feature-family ablation, chronological cross-validation, controlled feature and
recency/class-weight experiments, a bounded hyperparameter search, calibration
analysis, and a single frozen-test-set evaluation of the best challenger with an
explicit promotion decision.

All outputs go under outputs/reports/modeling/phase5g/ and outputs/models/phase5g/.
Production artifacts (outputs/models/selected_model.joblib, model_registry.json)
are never modified here. Promotion, if any, is a separate explicit step.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.modeling.data_loader import load_training_dataset
from src.modeling.evaluate import CLASSES, align_proba, multiclass_brier_score
from src.modeling.feature_selection import get_safe_feature_columns
from src.modeling.model_config import MODEL_DIR, RANDOM_SEED, TRAIN_FRACTION, VAL_FRACTION
from src.modeling.splits import chronological_train_val_test_split
from src.config import OUTPUTS_DIR

OUTDIR = OUTPUTS_DIR / "reports" / "modeling" / "phase5g"
CHALLENGER_DIR = MODEL_DIR / "phase5g"
CLASS_NAMES = {0: "team_a_loss", 1: "draw", 2: "team_a_win"}

PROD_XGB_PARAMS = dict(
    objective="multi:softprob", num_class=3, eval_metric="mlogloss",
    n_estimators=500, max_depth=3, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
    random_state=RANDOM_SEED, n_jobs=2,
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_dirs() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    CHALLENGER_DIR.mkdir(parents=True, exist_ok=True)


def _X(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[cols].apply(pd.to_numeric, errors="coerce")


def _proba(model, X) -> np.ndarray:
    p = model.predict_proba(X)
    classes = model.named_steps["model"].classes_ if hasattr(model, "named_steps") else getattr(model, "classes_", CLASSES)
    return align_proba(p, classes)


def _metrics(y_true, proba) -> dict:
    y_true = np.asarray(y_true)
    pred = proba.argmax(axis=1)
    prec, rec, f1, support = precision_recall_fscore_support(y_true, pred, labels=CLASSES, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, pred)),
        "macro_f1": float(f1_score(y_true, pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, pred, average="weighted", zero_division=0)),
        "log_loss": float(log_loss(y_true, proba, labels=CLASSES)),
        "brier_score": float(multiclass_brier_score(y_true, proba)),
        "precision": {CLASS_NAMES[c]: float(prec[i]) for i, c in enumerate(CLASSES)},
        "recall": {CLASS_NAMES[c]: float(rec[i]) for i, c in enumerate(CLASSES)},
        "f1": {CLASS_NAMES[c]: float(f1[i]) for i, c in enumerate(CLASSES)},
        "support": {CLASS_NAMES[c]: int(support[i]) for i, c in enumerate(CLASSES)},
        "actual_distribution": {CLASS_NAMES[c]: int((y_true == c).sum()) for c in CLASSES},
        "predicted_distribution": {CLASS_NAMES[c]: int((pred == c).sum()) for c in CLASSES},
    }


def _fit_xgb(Xtr, ytr, Xval, yval, params, sample_weight=None) -> XGBClassifier:
    model = XGBClassifier(**params)
    try:
        model.fit(Xtr, ytr, sample_weight=sample_weight, eval_set=[(Xval, yval)], verbose=False)
    except TypeError:
        model.fit(Xtr, ytr, sample_weight=sample_weight)
    return model


def _fit_logistic(Xtr, ytr) -> Pipeline:
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=RANDOM_SEED)),
    ])
    model.fit(Xtr, ytr)
    return model


def _confidence_bands(y_true, proba) -> list[dict]:
    conf = proba.max(axis=1)
    pred = proba.argmax(axis=1)
    correct = (pred == np.asarray(y_true)).astype(int)
    bands = [(0.33, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 1.01)]
    out = []
    for lo, hi in bands:
        mask = (conf >= lo) & (conf < hi)
        n = int(mask.sum())
        out.append({"band": f"{lo:.2f}-{min(hi,1.0):.2f}", "support": n,
                    "accuracy": float(correct[mask].mean()) if n else None,
                    "mean_confidence": float(conf[mask].mean()) if n else None})
    return out


def _ece(y_true, proba, n_bins=10) -> float:
    """Expected Calibration Error using top-label confidence."""
    conf = proba.max(axis=1)
    pred = proba.argmax(axis=1)
    correct = (pred == np.asarray(y_true)).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (conf > edges[i]) & (conf <= edges[i + 1])
        if mask.sum():
            ece += (mask.mean()) * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


# --------------------------------------------------------------------------- #
# Phase 5G-A + baseline freeze
# --------------------------------------------------------------------------- #

def diagnostics(train, val, test, feats) -> dict:
    Xtr, ytr = _X(train, feats), train["match_result"].to_numpy()
    Xval, yval = _X(val, feats), val["match_result"].to_numpy()
    Xte, yte = _X(test, feats), test["match_result"].to_numpy()

    lr = _fit_logistic(Xtr, ytr)
    xgb = _fit_xgb(Xtr, ytr, Xval, yval, PROD_XGB_PARAMS)

    out = {"models": {}}
    for name, model in [("logistic_regression", lr), ("xgboost", xgb)]:
        entry = {}
        for split, X, y in [("validation", Xval, yval), ("test", Xte, yte)]:
            proba = _proba(model, X)
            m = _metrics(y, proba)
            m["confusion_matrix"] = confusion_matrix(y, proba.argmax(axis=1), labels=CLASSES).tolist()
            m["ece"] = _ece(y, proba)
            if split == "test":
                m["confidence_bands"] = _confidence_bands(y, proba)
            entry[split] = m
        out["models"][name] = entry
    return out, lr, xgb


# --------------------------------------------------------------------------- #
# Phase 5G-B segmentation (baseline XGB on test)
# --------------------------------------------------------------------------- #

def segmentation(test, xgb, feats) -> pd.DataFrame:
    Xte = _X(test, feats)
    proba = _proba(xgb, Xte)
    pred = proba.argmax(axis=1)
    y = test["match_result"].to_numpy()
    d = test.copy()
    d["_pred"], d["_correct"] = pred, (pred == y).astype(int)

    def seg_row(label, mask):
        n = int(mask.sum())
        if n < 30:
            return {"segment": label, "support": n, "accuracy": None, "macro_f1": None, "log_loss": None}
        sub_y, sub_p = y[mask.to_numpy()], proba[mask.to_numpy()]
        return {"segment": label, "support": n,
                "accuracy": float(accuracy_score(sub_y, sub_p.argmax(axis=1))),
                "macro_f1": float(f1_score(sub_y, sub_p.argmax(axis=1), average="macro", zero_division=0)),
                "log_loss": float(log_loss(sub_y, sub_p, labels=CLASSES)),
                "draw_rate_actual": float((sub_y == 1).mean())}

    rows = []
    # By era/decade
    d["_decade"] = (d["date"].dt.year // 10 * 10)
    for dec in sorted(d["_decade"].dropna().unique()):
        rows.append(seg_row(f"decade_{int(dec)}s", d["_decade"] == dec))
    # By tournament type
    for label, col in [("world_cup", "is_world_cup_match"), ("friendly", "is_friendly"), ("qualifier", "is_qualifier")]:
        if col in d:
            flag = pd.to_numeric(d[col], errors="coerce").fillna(0) > 0
            rows.append(seg_row(f"tournament_{label}", flag))
            rows.append(seg_row(f"tournament_not_{label}", ~flag))
    # Competitive vs friendly
    if "is_friendly" in d:
        fr = pd.to_numeric(d["is_friendly"], errors="coerce").fillna(0) > 0
        rows.append(seg_row("competitive", ~fr))
    # Neutral venue
    if "is_neutral" in d:
        nt = pd.to_numeric(d["is_neutral"], errors="coerce").fillna(0) > 0
        rows.append(seg_row("neutral_venue", nt))
        rows.append(seg_row("non_neutral_venue", ~nt))
    # Elo-difference bands
    ad = d["elo_difference"].abs()
    for lo, hi in [(0, 50), (50, 100), (100, 200), (200, 300), (300, 1e9)]:
        rows.append(seg_row(f"abs_elo_diff_{lo}-{'inf' if hi>1e8 else int(hi)}", (ad >= lo) & (ad < hi)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Phase 5G-C ablation (train on train, evaluate on validation)
# --------------------------------------------------------------------------- #

FAMILIES = {
    "elo": ["team_a_pre_match_elo", "team_b_pre_match_elo", "elo_difference", "elo_expected_score_team_a"],
    "form": ["form_points_last_5_diff", "win_rate_last_5_diff", "loss_rate_last_5_diff"],
    "goals": ["goals_for_avg_last_5_diff", "goals_against_avg_last_5_diff", "goal_diff_avg_last_5_diff", "clean_sheet_rate_last_5_diff"],
    "h2h": ["h2h_matches_last_10", "h2h_team_a_win_rate_last_10", "h2h_goal_diff_team_a_last_10"],
    "tournament": ["is_world_cup_match", "is_friendly", "is_qualifier", "is_neutral", "tournament_importance_score"],
    "schedule": ["team_a_days_since_last_match", "team_b_days_since_last_match", "rest_days_diff", "team_a_matches_last_30_days", "team_b_matches_last_30_days", "match_congestion_diff"],
}


def ablation(train, val, feats) -> pd.DataFrame:
    ytr, yval = train["match_result"].to_numpy(), val["match_result"].to_numpy()
    configs = {
        "elo_only": FAMILIES["elo"],
        "elo+form": FAMILIES["elo"] + FAMILIES["form"],
        "elo+goals": FAMILIES["elo"] + FAMILIES["goals"],
        "elo+h2h": FAMILIES["elo"] + FAMILIES["h2h"],
        "elo+tournament": FAMILIES["elo"] + FAMILIES["tournament"],
        "elo+schedule": FAMILIES["elo"] + FAMILIES["schedule"],
        "full_production": feats,
    }
    rows = []
    for name, cols in configs.items():
        cols = [c for c in cols if c in train.columns]
        model = _fit_xgb(_X(train, cols), ytr, _X(val, cols), yval, PROD_XGB_PARAMS)
        m = _metrics(yval, _proba(model, _X(val, cols)))
        rows.append({"config": name, "n_features": len(cols), "val_accuracy": m["accuracy"],
                     "val_macro_f1": m["macro_f1"], "val_log_loss": m["log_loss"],
                     "val_brier": m["brier_score"], "val_draw_recall": m["recall"]["draw"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Phase 5G-E chronological CV (expanding window over train+val, test untouched)
# --------------------------------------------------------------------------- #

def chronological_cv(dev: pd.DataFrame, feats, params, sample_weight_fn=None, folds=4) -> list[dict]:
    dev = dev.sort_values("date").reset_index(drop=True)
    n = len(dev)
    start = int(n * 0.5)
    edges = np.linspace(start, n, folds + 1).astype(int)
    out = []
    for i in range(folds):
        tr = dev.iloc[: edges[i]]
        va = dev.iloc[edges[i]: edges[i + 1]]
        if len(va) < 100:
            continue
        sw = sample_weight_fn(tr) if sample_weight_fn else None
        model = _fit_xgb(_X(tr, feats), tr["match_result"].to_numpy(), _X(va, feats), va["match_result"].to_numpy(), params, sw)
        m = _metrics(va["match_result"].to_numpy(), _proba(model, _X(va, feats)))
        out.append({"fold": i + 1, "train_rows": len(tr), "val_rows": len(va),
                    "accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                    "log_loss": m["log_loss"], "brier": m["brier_score"]})
    return out


# --------------------------------------------------------------------------- #
# Phase 5G-D/G/A experiments + 5G-F tuning (all evaluated on validation)
# --------------------------------------------------------------------------- #

def _recency_weight(df: pd.DataFrame, half_life_years: float | None) -> np.ndarray | None:
    if not half_life_years:
        return None
    ref = df["date"].max()
    age = (ref - df["date"]).dt.days / 365.25
    return np.power(0.5, age / half_life_years).to_numpy()


def _balanced_weight(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=3)
    w = len(y) / (3 * np.maximum(counts, 1))
    return w[y]


def experiments(train, val, feats) -> tuple[pd.DataFrame, dict]:
    ytr, yval = train["match_result"].to_numpy(), val["match_result"].to_numpy()
    rng = np.random.default_rng(RANDOM_SEED)
    results = []

    def record(exp_id, family, cols, params, sw=None, note=""):
        model = _fit_xgb(_X(train, cols), ytr, _X(val, cols), yval, params, sw)
        m = _metrics(yval, _proba(model, _X(val, cols)))
        results.append({"experiment_id": exp_id, "family": family, "n_features": len(cols),
                        "val_accuracy": m["accuracy"], "val_macro_f1": m["macro_f1"],
                        "val_log_loss": m["log_loss"], "val_brier": m["brier_score"],
                        "val_draw_recall": m["recall"]["draw"], "val_draw_f1": m["f1"]["draw"],
                        "note": note})
        return m

    # Baseline reference on val
    record("E0_baseline", "baseline", feats, PROD_XGB_PARAMS, note="production features + params")

    # Experiment A — multi-window form (add last_3 + last_10 diffs, built from existing per-team cols)
    ext = train.copy(); extv = val.copy()
    multiwin = []
    for base in ["form_points", "win_rate", "goals_for_avg", "goals_against_avg", "goal_diff_avg"]:
        for w in [3, 10]:
            a, b = f"team_a_{base}_last_{w}", f"team_b_{base}_last_{w}"
            if a in train.columns and b in train.columns:
                col = f"{base}_last_{w}_diff"
                ext[col] = pd.to_numeric(ext[a], errors="coerce") - pd.to_numeric(ext[b], errors="coerce")
                extv[col] = pd.to_numeric(extv[a], errors="coerce") - pd.to_numeric(extv[b], errors="coerce")
                multiwin.append(col)
    # also draw_rate_last_5_diff (draw-signal feature)
    if "team_a_draw_rate_last_5" in train.columns:
        for frame in (ext, extv):
            frame["draw_rate_last_5_diff"] = pd.to_numeric(frame["team_a_draw_rate_last_5"], errors="coerce") - pd.to_numeric(frame["team_b_draw_rate_last_5"], errors="coerce")
        multiwin.append("draw_rate_last_5_diff")
    feats_A = feats + multiwin
    mA = _fit_xgb(_X(ext, feats_A), ytr, _X(extv, feats_A), yval, PROD_XGB_PARAMS)
    mAm = _metrics(yval, _proba(mA, _X(extv, feats_A)))
    results.append({"experiment_id": "A_multiwindow", "family": "feature", "n_features": len(feats_A),
                    "val_accuracy": mAm["accuracy"], "val_macro_f1": mAm["macro_f1"], "val_log_loss": mAm["log_loss"],
                    "val_brier": mAm["brier_score"], "val_draw_recall": mAm["recall"]["draw"], "val_draw_f1": mAm["f1"]["draw"],
                    "note": f"added {len(multiwin)} last_3/last_10 + draw_rate diffs"})

    # Experiment D — recency weighting
    for hl in [8.0, 4.0, 2.0]:
        record(f"D_recency_hl{hl:g}", "recency_weight", feats, PROD_XGB_PARAMS,
               sw=_recency_weight(train, hl), note=f"half-life {hl}y")

    # Experiment G — class weighting (draw investigation)
    record("G_balanced_weight", "class_weight", feats, PROD_XGB_PARAMS,
           sw=_balanced_weight(ytr), note="inverse-frequency class weights")
    draw_boost = np.where(ytr == 1, 1.8, 1.0)
    record("G_draw_boost", "class_weight", feats, PROD_XGB_PARAMS, sw=draw_boost, note="draw x1.8")

    # Experiment F — bounded randomized hyperparameter search (val log loss primary)
    best = {"val_log_loss": 1e9}
    search_rows = []
    grid = dict(max_depth=[3, 4, 5, 6], learning_rate=[0.02, 0.03, 0.05, 0.08],
                n_estimators=[300, 500, 800], min_child_weight=[1, 3, 5, 10],
                subsample=[0.7, 0.8, 0.9], colsample_bytree=[0.7, 0.8, 0.9],
                gamma=[0, 0.5, 1.0], reg_lambda=[0.5, 1.0, 2.0, 5.0], reg_alpha=[0, 0.5, 1.0])
    for it in range(30):
        params = dict(PROD_XGB_PARAMS)
        for k, choices in grid.items():
            params[k] = float(rng.choice(choices)) if k in ("learning_rate", "subsample", "colsample_bytree", "gamma", "reg_lambda", "reg_alpha") else int(rng.choice(choices))
        model = _fit_xgb(_X(train, feats), ytr, _X(val, feats), yval, params)
        m = _metrics(yval, _proba(model, _X(val, feats)))
        row = {"iter": it, **{k: params[k] for k in grid}, "val_log_loss": m["log_loss"],
               "val_accuracy": m["accuracy"], "val_macro_f1": m["macro_f1"], "val_brier": m["brier_score"]}
        search_rows.append(row)
        if m["log_loss"] < best["val_log_loss"]:
            best = {"params": {k: params[k] for k in grid}, **row}
    results.append({"experiment_id": "F_tuned_best", "family": "hyperparameter", "n_features": len(feats),
                    "val_accuracy": best["val_accuracy"], "val_macro_f1": best["val_macro_f1"],
                    "val_log_loss": best["val_log_loss"], "val_brier": best["val_brier"],
                    "val_draw_recall": None, "val_draw_f1": None, "note": "best of 30 randomized configs"})

    pd.DataFrame(search_rows).to_csv(OUTDIR / "hyperparameter_search_results.csv", index=False)
    return pd.DataFrame(results), best


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def _bootstrap_acc_ci(y, proba_base, proba_chal, n=2000):
    y = np.asarray(y)
    base_c = (proba_base.argmax(axis=1) == y).astype(int)
    chal_c = (proba_chal.argmax(axis=1) == y).astype(int)
    rng = np.random.default_rng(RANDOM_SEED)
    diffs = []
    idx = np.arange(len(y))
    for _ in range(n):
        s = rng.choice(idx, size=len(y), replace=True)
        diffs.append(chal_c[s].mean() - base_c[s].mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(base_c.mean()), float(chal_c.mean()), float(lo), float(hi)


def run_phase5g(hyper_iters: int = 30) -> dict:
    t0 = time.perf_counter()
    _ensure_dirs()
    df = load_training_dataset()
    feats = get_safe_feature_columns(df)
    train, val, test = chronological_train_val_test_split(df)
    dev = pd.concat([train, val]).sort_values("date").reset_index(drop=True)
    dataset_fp = f"rows={len(df)};cols={len(df.columns)};min={df['date'].min().date()};max={df['date'].max().date()}"

    # A: diagnostics + baseline
    diag, lr, xgb = diagnostics(train, val, test, feats)
    baseline = {"model": "xgboost", "params": PROD_XGB_PARAMS, "features": feats,
                "validation": diag["models"]["xgboost"]["validation"], "test": diag["models"]["xgboost"]["test"],
                "frozen_at": _now(), "note": "Immutable Phase 5G production baseline reference."}
    (OUTDIR / "baseline_model_metrics.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    (OUTDIR / "diagnostic_metrics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    cms = {f"{name}_{split}": diag["models"][name][split]["confusion_matrix"] for name in diag["models"] for split in ("validation", "test")}
    (OUTDIR / "confusion_matrices.json").write_text(json.dumps({"labels": [CLASS_NAMES[c] for c in CLASSES], "matrices": cms}, indent=2), encoding="utf-8")
    reports = {name: {split: {k: diag["models"][name][split][k] for k in ("precision", "recall", "f1", "support", "macro_f1", "weighted_f1", "balanced_accuracy", "accuracy")} for split in ("validation", "test")} for name in diag["models"]}
    (OUTDIR / "classification_reports.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")

    # B: segmentation
    seg = segmentation(test, xgb, feats)
    seg.to_csv(OUTDIR / "segmented_performance.csv", index=False)

    # C: ablation
    abl = ablation(train, val, feats)
    abl.to_csv(OUTDIR / "feature_ablation_results.csv", index=False)

    # D/G/A + F: experiments
    exp, best = experiments(train, val, feats)
    exp.to_csv(OUTDIR / "feature_experiment_results.csv", index=False)

    # E: chronological CV (baseline params + best-tuned params)
    cv_base = chronological_cv(dev, feats, PROD_XGB_PARAMS)
    cv_best = chronological_cv(dev, feats, {**PROD_XGB_PARAMS, **best["params"]})
    cv_rows = [{"config": "baseline", **r} for r in cv_base] + [{"config": "tuned", **r} for r in cv_best]
    pd.DataFrame(cv_rows).to_csv(OUTDIR / "chronological_cv_results.csv", index=False)

    def cv_summary(rows):
        a = np.array([r["accuracy"] for r in rows]); ll = np.array([r["log_loss"] for r in rows]); mf = np.array([r["macro_f1"] for r in rows])
        return {"folds": len(rows), "mean_accuracy": float(a.mean()), "std_accuracy": float(a.std()),
                "mean_log_loss": float(ll.mean()), "mean_macro_f1": float(mf.mean())}

    # Challenger selection: best validation-log-loss config from the search (tuned params, production features).
    # Evaluate ONCE on the frozen test set.
    Xtr_dev, ytr_dev = _X(train, feats), train["match_result"].to_numpy()
    Xval, yval = _X(val, feats), val["match_result"].to_numpy()
    Xte, yte = _X(test, feats), test["match_result"].to_numpy()
    challenger = _fit_xgb(Xtr_dev, ytr_dev, Xval, yval, {**PROD_XGB_PARAMS, **best["params"]})
    chal_proba = _proba(challenger, Xte)
    base_proba = _proba(xgb, Xte)
    chal_test = _metrics(yte, chal_proba); chal_test["ece"] = _ece(yte, chal_proba)
    base_test = diag["models"]["xgboost"]["test"]
    b_acc, c_acc, ci_lo, ci_hi = _bootstrap_acc_ci(yte, base_proba, chal_proba)

    comparison = pd.DataFrame([
        {"model": "baseline_xgboost", "test_accuracy": base_test["accuracy"], "test_macro_f1": base_test["macro_f1"],
         "test_log_loss": base_test["log_loss"], "test_brier": base_test["brier_score"], "test_ece": base_test["ece"]},
        {"model": "challenger_tuned_xgboost", "test_accuracy": chal_test["accuracy"], "test_macro_f1": chal_test["macro_f1"],
         "test_log_loss": chal_test["log_loss"], "test_brier": chal_test["brier_score"], "test_ece": chal_test["ece"]},
    ])
    comparison.to_csv(OUTDIR / "challenger_model_comparison.csv", index=False)

    # Promotion decision (honest, probability-aware)
    acc_gain = chal_test["accuracy"] - base_test["accuracy"]
    ll_change = chal_test["log_loss"] - base_test["log_loss"]
    brier_change = chal_test["brier_score"] - base_test["brier_score"]
    ci_excludes_zero = ci_lo > 0
    cv_base_s, cv_best_s = cv_summary(cv_base), cv_summary(cv_best)
    meaningful = acc_gain >= 0.005 and ci_excludes_zero
    prob_ok = ll_change <= 0.002 and brier_change <= 0.002
    stable = cv_best_s["mean_log_loss"] <= cv_base_s["mean_log_loss"] + 0.005
    promote = bool(meaningful and prob_ok and stable)
    decision = {
        "generated_at": _now(), "promote": promote,
        "production_model_unchanged": not promote,
        "baseline_test": {k: base_test[k] for k in ("accuracy", "macro_f1", "log_loss", "brier_score", "ece")},
        "challenger_test": {k: chal_test[k] for k in ("accuracy", "macro_f1", "log_loss", "brier_score", "ece")},
        "challenger_params": best["params"],
        "test_accuracy_gain": acc_gain,
        "bootstrap_acc_diff_95ci": [ci_lo, ci_hi], "ci_excludes_zero": ci_excludes_zero,
        "log_loss_change": ll_change, "brier_change": brier_change,
        "cv_baseline": cv_base_s, "cv_tuned": cv_best_s,
        "rules": {"meaningful_accuracy_gain(>=0.005 & CI>0)": meaningful,
                  "probability_quality_preserved(logloss&brier not worse >0.002)": prob_ok,
                  "cv_stable": stable},
        "rationale": (
            "Challenger promoted: meaningful, statistically supported accuracy gain with preserved probability quality and stable CV."
            if promote else
            "Challenger REJECTED — production XGBoost retained. The tuned challenger did not clear all gates "
            "(meaningful+significant accuracy gain AND preserved log loss/Brier AND CV stability). "
            "Per Phase 5G rules, no model change is forced.")
    }
    (OUTDIR / "promotion_decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")

    # Experiment registry
    registry = {
        "phase": "5G_model_diagnostics", "generated_at": _now(), "dataset_fingerprint": dataset_fp,
        "random_seed": RANDOM_SEED, "features": feats, "feature_count": len(feats),
        "split": {"train_rows": len(train), "val_rows": len(val), "test_rows": len(test),
                  "train_dates": [str(train['date'].min().date()), str(train['date'].max().date())],
                  "val_dates": [str(val['date'].min().date()), str(val['date'].max().date())],
                  "test_dates": [str(test['date'].min().date()), str(test['date'].max().date())],
                  "fractions": [TRAIN_FRACTION, VAL_FRACTION, 1 - TRAIN_FRACTION - VAL_FRACTION]},
        "experiments": exp.to_dict(orient="records"),
        "ablation": abl.to_dict(orient="records"),
        "cv_baseline": cv_base_s, "cv_tuned": cv_best_s,
        "challenger_params": best["params"], "promotion": {"promote": promote},
    }
    (OUTDIR / "experiment_registry.json").write_text(json.dumps(registry, indent=2, default=str), encoding="utf-8")

    manifest = {
        "phase": "Phase 5G — Leakage-Safe Model Diagnostics, Feature Optimization & Challenger Evaluation",
        "generated_at": _now(), "dataset_fingerprint": dataset_fp, "random_seed": RANDOM_SEED,
        "python": platform.python_version(), "numpy": np.__version__, "seconds": round(time.perf_counter() - t0, 1),
        "artifacts": sorted(p.name for p in OUTDIR.glob("*")),
        "promotion": {"promote": promote, "production_model": "xgboost (unchanged)" if not promote else "challenger_tuned_xgboost"},
    }
    (OUTDIR / "phase_5g_audit_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"promote": promote, "baseline_test": base_test, "challenger_test": chal_test,
            "decision": decision, "seconds": manifest["seconds"], "outdir": str(OUTDIR)}
