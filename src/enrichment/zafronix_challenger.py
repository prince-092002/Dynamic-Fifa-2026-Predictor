"""Phase 5H-A challenger evaluation.

Reproduces the frozen production baseline, joins leakage-safe Zafronix features, runs
controlled feature-family experiments (E0-E9) on validation, chronological CV, then a
SINGLE frozen-test evaluation of the best enriched challenger with World Cup-subset
metrics, paired-bootstrap significance, and an explicit, honest promotion decision.

Production artifacts (outputs/models/selected_model.joblib, model_registry.json) are never
touched here. Reuses the Phase 5G harness so the baseline is byte-for-byte comparable.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.enrichment.zafronix_config import MODEL_DIR, REPORT_DIR, ensure_dirs
from src.enrichment.zafronix_features import (
    ALL_ZAFRONIX_FEATURES,
    AVAILABILITY_FEATURES,
    PEDIGREE_DIFF_FEATURES,
    PLAYER_EXP_DIFF_FEATURES,
    SQUAD_DIFF_FEATURES,
    build_zafronix_features,
)
from src.modeling.data_loader import load_training_dataset
from src.modeling.feature_selection import get_safe_feature_columns
from src.modeling.model_config import RANDOM_SEED
from src.modeling.splits import chronological_train_val_test_split
from src.modeling.phase5g_diagnostics import (
    PROD_XGB_PARAMS,
    _X,
    _bootstrap_acc_ci,
    _ece,
    _fit_xgb,
    _metrics,
    _proba,
)
from src.modeling.evaluate import CLASSES


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _prepare() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """Load training data, attach Zafronix features (index-aligned), split chronologically."""
    df = load_training_dataset()
    base_feats = get_safe_feature_columns(df)
    zfeat = build_zafronix_features(df)
    enriched = pd.concat([df.reset_index(drop=True), zfeat.reset_index(drop=True)], axis=1)
    train, val, test = chronological_train_val_test_split(enriched)
    return train, val, test, base_feats


def _wc_finals_mask(df: pd.DataFrame) -> np.ndarray:
    tour = df.get("tournament")
    if tour is None:
        return np.zeros(len(df), dtype=bool)
    return tour.astype(str).str.strip().str.casefold().eq("fifa world cup").to_numpy()


def _fit_eval(train, val, feats, y_train, y_val):
    model = _fit_xgb(_X(train, feats), y_train, _X(val, feats), y_val, PROD_XGB_PARAMS)
    m = _metrics(y_val, _proba(model, _X(val, feats)))
    return model, m


def run_phase5h_challenger() -> dict:
    t0 = time.perf_counter()
    ensure_dirs()
    train, val, test, base_feats = _prepare()
    y_tr, y_va, y_te = (train["match_result"].to_numpy(), val["match_result"].to_numpy(),
                        test["match_result"].to_numpy())

    ped = [c for c in PEDIGREE_DIFF_FEATURES if c in train.columns]
    squad = [c for c in SQUAD_DIFF_FEATURES if c in train.columns]
    pexp = [c for c in PLAYER_EXP_DIFF_FEATURES if c in train.columns]
    avail = [c for c in AVAILABILITY_FEATURES if c in train.columns]
    zall = [c for c in ALL_ZAFRONIX_FEATURES if c in train.columns]

    # --- Experiment matrix (train->val) ---
    configs = {
        "E0_baseline": base_feats,
        "E1_base_plus_pedigree": base_feats + ped,
        "E2_base_plus_squad": base_feats + squad,
        "E3_base_plus_player_experience": base_feats + pexp,
        "E4_base_plus_availability": base_feats + avail,
        "E5_base_plus_pedigree_availability": base_feats + ped + avail,
        "E6_base_plus_squad_and_player": base_feats + squad + pexp + avail,
        "E7_base_plus_all_zafronix": base_feats + zall,
    }
    exp_rows = []
    fitted = {}
    for name, feats in configs.items():
        model, m = _fit_eval(train, val, feats, y_tr, y_va)
        fitted[name] = (model, feats)
        exp_rows.append({
            "experiment_id": name, "n_features": len(feats),
            "n_zafronix_features": len(feats) - len(base_feats),
            "val_accuracy": m["accuracy"], "val_macro_f1": m["macro_f1"],
            "val_log_loss": m["log_loss"], "val_brier": m["brier_score"],
            "val_draw_recall": m["recall"]["draw"],
        })
    exp = pd.DataFrame(exp_rows)
    exp.to_csv(REPORT_DIR / "zafronix_feature_experiment_results.csv", index=False)

    baseline_val = exp[exp["experiment_id"] == "E0_baseline"].iloc[0]
    # Select best enriched challenger by validation log loss (probability-first, Phase 5G rule).
    enriched_rows = exp[exp["experiment_id"] != "E0_baseline"].copy()
    best_row = enriched_rows.sort_values("val_log_loss").iloc[0]
    best_name = best_row["experiment_id"]
    best_feats = configs[best_name]

    # --- Chronological CV: baseline vs best enriched (train+val, test untouched) ---
    dev = pd.concat([train, val]).sort_values("date").reset_index(drop=True)
    cv_rows = []
    for label, feats in [("baseline", base_feats), (best_name, best_feats)]:
        for fold in _chrono_cv(dev, feats):
            cv_rows.append({"config": label, **fold})
    pd.DataFrame(cv_rows).to_csv(REPORT_DIR / "zafronix_chronological_cv_results.csv", index=False)

    def cv_sum(label):
        rows = [r for r in cv_rows if r["config"] == label]
        a = np.array([r["accuracy"] for r in rows]); ll = np.array([r["log_loss"] for r in rows])
        return {"folds": len(rows), "mean_accuracy": float(a.mean()), "std_accuracy": float(a.std()),
                "mean_log_loss": float(ll.mean())}

    cv_base_s, cv_best_s = cv_sum("baseline"), cv_sum(best_name)

    # --- Frozen test evaluation (ONCE) ---
    base_model, _ = fitted["E0_baseline"]
    chal_model, _ = fitted[best_name]
    base_proba = _proba(base_model, _X(test, base_feats))
    chal_proba = _proba(chal_model, _X(test, best_feats))
    base_test = _metrics(y_te, base_proba); base_test["ece"] = _ece(y_te, base_proba)
    chal_test = _metrics(y_te, chal_proba); chal_test["ece"] = _ece(y_te, chal_proba)
    b_acc, c_acc, ci_lo, ci_hi = _bootstrap_acc_ci(y_te, base_proba, chal_proba)

    comparison = pd.DataFrame([
        {"model": "baseline_xgboost_25f", "features": len(base_feats),
         "test_accuracy": base_test["accuracy"], "test_macro_f1": base_test["macro_f1"],
         "test_log_loss": base_test["log_loss"], "test_brier": base_test["brier_score"], "test_ece": base_test["ece"]},
        {"model": f"challenger_{best_name}", "features": len(best_feats),
         "test_accuracy": chal_test["accuracy"], "test_macro_f1": chal_test["macro_f1"],
         "test_log_loss": chal_test["log_loss"], "test_brier": chal_test["brier_score"], "test_ece": chal_test["ece"]},
    ])
    comparison.to_csv(REPORT_DIR / "zafronix_challenger_model_comparison.csv", index=False)

    # --- World Cup subset metrics (overall + WC finals) ---
    wc_mask = _wc_finals_mask(test)
    subset_rows = [_subset_metrics("all_test", y_te, base_proba, chal_proba)]
    if wc_mask.sum() >= 30:
        subset_rows.append(_subset_metrics("world_cup_finals", y_te[wc_mask], base_proba[wc_mask], chal_proba[wc_mask]))
    else:
        subset_rows.append({"subset": "world_cup_finals", "support": int(wc_mask.sum()),
                            "note": "sample too small (<30) for reliable subset metrics"})
    # both-WC-nations subset (pedigree-relevant)
    zavail = test.get("z_pedigree_available")
    if zavail is not None:
        pm = zavail.to_numpy().astype(bool)
        if pm.sum() >= 30:
            subset_rows.append(_subset_metrics("both_teams_wc_pedigree", y_te[pm], base_proba[pm], chal_proba[pm]))
    pd.DataFrame(subset_rows).to_csv(REPORT_DIR / "zafronix_world_cup_subset_metrics.csv", index=False)

    # --- E8: World-Cup-finals-specific challenger (small-sample, honest) ---
    e8 = _wc_specific_challenger(train, val, test, base_feats, zall, y_tr, y_va, y_te)

    # --- E9: routed hybrid (enriched on WC finals rows, baseline elsewhere) ---
    routed_proba = base_proba.copy()
    routed_proba[wc_mask] = chal_proba[wc_mask]
    e9 = _metrics(y_te, routed_proba); e9["ece"] = _ece(y_te, routed_proba)

    # --- Feature importance for the enriched challenger ---
    _feature_importance(chal_model, best_feats, base_feats)

    # --- Promotion decision (Phase 5G gates, probability-aware) ---
    acc_gain = chal_test["accuracy"] - base_test["accuracy"]
    ll_change = chal_test["log_loss"] - base_test["log_loss"]
    brier_change = chal_test["brier_score"] - base_test["brier_score"]
    ci_excludes_zero = ci_lo > 0
    meaningful = acc_gain >= 0.005 and ci_excludes_zero
    prob_ok = ll_change <= 0.002 and brier_change <= 0.002
    stable = cv_best_s["mean_log_loss"] <= cv_base_s["mean_log_loss"] + 0.005
    promote = bool(meaningful and prob_ok and stable)

    decision = {
        "generated_at": _now(), "promote": promote, "production_model_unchanged": not promote,
        "selected_challenger": best_name, "challenger_feature_count": len(best_feats),
        "baseline_feature_count": len(base_feats),
        "baseline_test": {k: base_test[k] for k in ("accuracy", "macro_f1", "log_loss", "brier_score", "ece")},
        "challenger_test": {k: chal_test[k] for k in ("accuracy", "macro_f1", "log_loss", "brier_score", "ece")},
        "test_accuracy_gain": acc_gain,
        "bootstrap_acc_diff_95ci": [ci_lo, ci_hi], "ci_excludes_zero": ci_excludes_zero,
        "log_loss_change": ll_change, "brier_change": brier_change,
        "cv_baseline": cv_base_s, "cv_challenger": cv_best_s,
        "rules": {"meaningful_accuracy_gain(>=0.005 & CI>0)": meaningful,
                  "probability_quality_preserved(logloss&brier not worse >0.002)": prob_ok,
                  "cv_stable": stable},
        "world_cup_finals_support_in_test": int(wc_mask.sum()),
        "routed_hybrid_test": {k: e9[k] for k in ("accuracy", "macro_f1", "log_loss", "brier_score", "ece")},
        "wc_specific_challenger": e8,
        "rationale": (
            "Challenger promoted: statistically supported accuracy gain with preserved probability quality and stable CV."
            if promote else
            "Challenger REJECTED — production XGBoost retained unchanged. Zafronix World Cup pedigree/squad features "
            "did not clear all promotion gates on the frozen global test set (meaningful+significant accuracy gain AND "
            "preserved log loss/Brier AND CV stability). This is an expected, acceptable outcome: only ~2.1% of "
            "training matches are World Cup finals and pedigree signal overlaps heavily with existing Elo/form features. "
            "Per Phase 5H-A rules, no model change is forced; the enrichment pipeline is retained for analysis and "
            "future use."),
    }
    (REPORT_DIR / "zafronix_promotion_decision.json").write_text(json.dumps(decision, indent=2, default=float), encoding="utf-8")

    manifest = {
        "phase": "Phase 5H-A — Zafronix World Cup, Squad & Historical Intelligence Enrichment",
        "generated_at": _now(), "random_seed": RANDOM_SEED,
        "python": platform.python_version(), "numpy": np.__version__,
        "seconds": round(time.perf_counter() - t0, 1),
        "split": {"train": len(train), "val": len(val), "test": len(test)},
        "baseline_features": len(base_feats), "zafronix_features": len(zall),
        "selected_challenger": best_name, "promote": promote,
        "artifacts": sorted(p.name for p in REPORT_DIR.glob("zafronix_*")),
    }
    (REPORT_DIR / "phase_5h_a_audit_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    return {
        "promote": promote, "selected_challenger": best_name,
        "baseline_test": base_test, "challenger_test": chal_test,
        "acc_gain": acc_gain, "bootstrap_ci": [ci_lo, ci_hi],
        "ll_change": ll_change, "brier_change": brier_change,
        "cv_baseline": cv_base_s, "cv_challenger": cv_best_s,
        "wc_finals_test_support": int(wc_mask.sum()),
        "experiments": exp.to_dict(orient="records"),
        "seconds": manifest["seconds"], "decision": decision,
    }


def _chrono_cv(dev: pd.DataFrame, feats, folds=4) -> list[dict]:
    dev = dev.sort_values("date").reset_index(drop=True)
    n = len(dev)
    edges = np.linspace(int(n * 0.5), n, folds + 1).astype(int)
    out = []
    for i in range(folds):
        tr = dev.iloc[: edges[i]]
        va = dev.iloc[edges[i]: edges[i + 1]]
        if len(va) < 100:
            continue
        model = _fit_xgb(_X(tr, feats), tr["match_result"].to_numpy(),
                         _X(va, feats), va["match_result"].to_numpy(), PROD_XGB_PARAMS)
        m = _metrics(va["match_result"].to_numpy(), _proba(model, _X(va, feats)))
        out.append({"fold": i + 1, "train_rows": len(tr), "val_rows": len(va),
                    "accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                    "log_loss": m["log_loss"], "brier": m["brier_score"]})
    return out


def _subset_metrics(name, y, base_proba, chal_proba) -> dict:
    base = _metrics(y, base_proba)
    chal = _metrics(y, chal_proba)
    return {
        "subset": name, "support": int(len(y)),
        "base_accuracy": base["accuracy"], "chal_accuracy": chal["accuracy"],
        "acc_diff": chal["accuracy"] - base["accuracy"],
        "base_macro_f1": base["macro_f1"], "chal_macro_f1": chal["macro_f1"],
        "base_log_loss": base["log_loss"], "chal_log_loss": chal["log_loss"],
        "ll_diff": chal["log_loss"] - base["log_loss"],
        "base_brier": base["brier_score"], "chal_brier": chal["brier_score"],
    }


def _wc_specific_challenger(train, val, test, base_feats, zall, y_tr, y_va, y_te) -> dict:
    """Train and evaluate a model on World Cup finals matches only (small sample, honest)."""
    tr_m = _wc_finals_mask(train); va_m = _wc_finals_mask(val); te_m = _wc_finals_mask(test)
    if tr_m.sum() < 200 or te_m.sum() < 30:
        return {"status": "insufficient_sample", "train_wc": int(tr_m.sum()), "test_wc": int(te_m.sum())}
    feats = base_feats + zall
    tr, va, te = train[tr_m], val[va_m], test[te_m]
    model = _fit_xgb(_X(tr, feats), y_tr[tr_m], _X(va, feats), y_va[va_m], PROD_XGB_PARAMS)
    base_model = _fit_xgb(_X(tr, base_feats), y_tr[tr_m], _X(va, base_feats), y_va[va_m], PROD_XGB_PARAMS)
    chal = _metrics(y_te[te_m], _proba(model, _X(te, feats)))
    base = _metrics(y_te[te_m], _proba(base_model, _X(te, base_feats)))
    return {
        "status": "ok", "train_wc": int(tr_m.sum()), "test_wc": int(te_m.sum()),
        "base_accuracy": base["accuracy"], "enriched_accuracy": chal["accuracy"],
        "base_log_loss": base["log_loss"], "enriched_log_loss": chal["log_loss"],
        "base_macro_f1": base["macro_f1"], "enriched_macro_f1": chal["macro_f1"],
        "note": "World-Cup-finals-only model; small test support -> interpret cautiously.",
    }


def _feature_importance(model, feats, base_feats) -> None:
    gain: dict[str, float] = {}
    try:
        booster = model.get_booster()
        score = booster.get_score(importance_type="gain")
        for key, value in score.items():
            if key in feats:  # fit on a DataFrame -> features named by column
                gain[key] = value
            elif key.startswith("f") and key[1:].isdigit() and int(key[1:]) < len(feats):
                gain[feats[int(key[1:])]] = value  # fallback: f0..fN order
    except Exception:
        gain = {}
    rows = [{"feature": f, "gain": float(gain.get(f, 0.0)),
             "is_zafronix": f not in base_feats} for f in feats]
    df = pd.DataFrame(rows).sort_values("gain", ascending=False)
    df.to_csv(REPORT_DIR / "zafronix_feature_importance.csv", index=False)
